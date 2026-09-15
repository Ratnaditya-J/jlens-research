"""Protocol adapter preserving the pinned PEFT weights, tokenizer and final norm."""
import json
from pathlib import Path

def load_model(root):
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    cfg = json.loads((Path(root)/'configs/identity-fp32.json').read_text())
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    locations = {k: snapshot_download(cfg[k]['repo'], revision=cfg[k]['revision'],
                    cache_dir='/workspace/hf-cache', local_files_only=True) for k in ('base', 'adapter')}
    tokenizer = AutoTokenizer.from_pretrained(locations['base'], trust_remote_code=False)
    hf = AutoModelForCausalLM.from_pretrained(locations['base'], dtype=torch.float32,
        device_map={'': 'cuda:0'}, attn_implementation='eager', trust_remote_code=False, use_safetensors=True)
    model = PeftModel.from_pretrained(hf, locations['adapter'], is_trainable=False).eval()
    for parameter in model.parameters(): parameter.requires_grad_(False)
    assert sum('lora_' in name for name, _ in model.named_parameters()) == 192
    return GPTOSSLensModel(model, tokenizer)

class GPTOSSLensModel:
    def __init__(self, model, tokenizer):
        self.peft_model = model
        self.base = model.get_base_model()
        self.layers = self.base.model.layers
        self.n_layers = len(self.layers)
        self.d_model = self.base.config.hidden_size
        self.tokenizer = tokenizer

    def encode(self, text, *, max_length=128):
        # Generic text uses native tokenizer behavior, without changing BOS or
        # wrapping it in the behavioral chat template.
        return self.tokenizer(text, return_tensors='pt', truncation=True,
                              max_length=max_length).input_ids.to('cuda')

    def forward(self, input_ids):
        # PEFT has already installed the LoRA modules inside this residual stack.
        return self.base.model(input_ids=input_ids, use_cache=False)

    def unembed(self, residual):
        return self.base.lm_head(self.base.model.norm(residual))
