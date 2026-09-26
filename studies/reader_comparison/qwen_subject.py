"""Subject adapter with explicit identity; never disables the organism LoRA."""
import json
from pathlib import Path


class QwenSubject:
    def __init__(self, config, dtype='float32'):
        import torch
        from transformers import AutoModelForImageTextToText, AutoTokenizer
        from huggingface_hub import snapshot_download
        from peft import PeftModel
        self.config = config
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        base=snapshot_download(repo_id=config['base']['repo'],revision=config['base']['revision'],allow_patterns=['*.json','*.jinja','*.txt','*.safetensors'],local_files_only=True)
        adapter=snapshot_download(repo_id=config['subject_adapter']['repo'],revision=config['subject_adapter']['revision'],allow_patterns=['adapter_config.json','adapter_model.safetensors'],local_files_only=True)
        self.tokenizer=AutoTokenizer.from_pretrained(base)
        raw=AutoModelForImageTextToText.from_pretrained(base,dtype=getattr(torch,dtype),device_map='cuda',attn_implementation='eager')
        self.model=PeftModel.from_pretrained(raw,adapter,is_trainable=False).eval()
        for p in self.model.parameters():p.requires_grad_(False)
        self.base=self.model.get_base_model()
        self.decoder=self.base.model.language_model
        self.layers=self.decoder.layers
        self.n_layers=len(self.layers)
        self.d_model=self.base.config.text_config.hidden_size
        assert self.n_layers==64 and self.d_model==5120
        self.identity={'base':config['base'],'adapter':config['subject_adapter'],'adapter_enabled':True,'adapter_merged':False,'dtype':dtype,'attention':'eager','tf32':False}

    def encode(self,text,*,max_length=128):
        return self.tokenizer(text,return_tensors='pt',truncation=True,max_length=max_length).input_ids.cuda()

    def forward(self,input_ids):
        # LoRA modules have been installed into this decoder. Calling the decoder
        # avoids an unnecessary all-position vocabulary projection while fitting.
        return self.decoder(input_ids=input_ids,use_cache=False)

    def unembed(self,h):
        return self.base.get_output_embeddings()(self.decoder.norm(h))

    def capture(self,ids,layers,positions):
        import torch
        states={}
        def make_hook(layer):
            def hook(_m,_i,out):
                h=out[0] if isinstance(out,tuple) else out
                states[layer]=h[0,positions].detach().float().cpu()
            return hook
        handles=[self.layers[l].register_forward_hook(make_hook(l)) for l in layers]
        try:
            with torch.no_grad():self.forward(torch.tensor([ids],device='cuda'))
        finally:
            for handle in handles:handle.remove()
        return states
