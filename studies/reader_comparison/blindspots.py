"""Report probe-positive display failures without requiring Oracle availability."""
def probe_display_blindspots(rows, thresholds):
    output={k:[] for k in ['probe_detected_jtokens_missed','probe_detected_jsummary_missed','probe_detected_jdisplay_missed','probe_detected_jdisplay_unavailable']}
    def flag(row, arm):
        score=row['scores'].get(arm)
        return None if score is None else bool(score>=thresholds[arm])
    for row in rows:
        if row['label']!=1 or flag(row,'raw_probe') is not True:
            continue
        token=flag(row,'j_tokens_context');summary=flag(row,'j_summary_context')
        record={'episode_id':row['episode_id'], 'j_tokens_context_detected':token,
                'j_summary_context_detected':summary,'jspace_probe_detected':flag(row,'jspace_probe'),
                'oracle_detected':flag(row,'oracle_context'),'context_detected':flag(row,'context_only'),
                'strict_confirmation':row.get('strict_confirmation')}
        if token is False:output['probe_detected_jtokens_missed'].append(record)
        if summary is False:output['probe_detected_jsummary_missed'].append(record)
        if token is False and summary is False:output['probe_detected_jdisplay_missed'].append(record)
        if token is None or summary is None:output['probe_detected_jdisplay_unavailable'].append(record)
    output['probe_display_blindspot_scope']='Known-positive behavior episodes detected by the raw probe. Token and summary flags use their contextual arms and frozen thresholds. Missing Oracle scores do not exclude cases; unavailable J views are not negative detections. A joint display miss does not imply loss of information in the full J-space vector.'
    return output
