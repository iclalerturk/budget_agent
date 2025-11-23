import json
import pandas as pd
from rapidfuzz import fuzz, process
import re

# --- yardımcı fonksiyonlar ---
def to_numeric_safe(series):
    return (
        series.astype(str)
        .str.replace(r"[^\d\.-]", "", regex=True)
        .replace("", "0")
        .astype(float)
    )

def normalize_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip().lower()

# --- filtreleme ---
def apply_filter(df_local, filt_local, threshold=75, top_n=5):
    if not (filt_local and isinstance(filt_local, dict)):
        return df_local
    filt_norm = {normalize_text(k): normalize_text(v) for k, v in filt_local.items()}

    for k, v in filt_norm.items():
        if k not in df_local.columns:
            print(f"Filtre kolon bulunamadı: {k}")
            continue

        candidates = pd.Series(df_local[k].unique()).astype(str).tolist()

        if v in candidates:
            df_local = df_local[df_local[k] == v]
            continue

        mask = df_local[k].str.contains(re.escape(v), na=False)
        if mask.any():
            df_local = df_local[mask]
            continue

        matches = process.extract(v, candidates, scorer=fuzz.token_set_ratio, limit=top_n)
        if matches:
            best_value, best_score, _ = matches[0]
            dynamic_threshold = threshold if len(v) <= 20 else max(55, threshold - 10)
            if best_score >= dynamic_threshold:
                print(f"Fuzzy eşleşme: '{v}' ≈ '{best_value}' ({best_score}%)")
                df_local = df_local[df_local[k] == best_value]
                continue

        if matches:
            best_value = matches[0][0]
            print(f"Fallback eşleşme: '{v}' ≈ '{best_value}'")
            df_local = df_local[df_local[k] == best_value]

    return df_local

# --- temel işlem fonksiyonu ---
def apply_op(series, op_name, source_series=None, mode="together"):
    if op_name == "sum":
        return series.sum()
    elif op_name == "max":
        return series.max()
    elif op_name == "min":
        return series.min()
    elif op_name == "avg":
        return series.mean()
    elif op_name == "diff":
        print("apply_op diff çağrıldı")
           
        return series.sum() - source_series.sum()
    elif op_name == "ratio":
        t_sum = series.sum() if series is not None else 0
        s_sum = source_series.sum() if source_series is not None else 0
        return (t_sum / s_sum) * 100 if s_sum != 0 else None
    
    elif op_name == "percentage_change":
        # if len(series) >= 2 and series.iloc[0] != 0:
        #     return ((series.iloc[-1] - series.iloc[0]) / series.iloc[0]) * 100
        # else:
        #     return None
        print("-----",series.sum(), source_series.sum())
        result=((series.sum() *100) / source_series.sum())  if source_series.sum() != 0 else None
        return result-100
    elif op_name == "list":
        return series.tolist()
    else:
        print("Tanımlı olmayan işlem:", op_name)
        return None

# --- ana execute fonksiyonu ---
def execute_instruction(doc_list, instruction_json):
    try:
        instr = json.loads(instruction_json)
        print("Parsed instruction:", instr)
    except json.JSONDecodeError:
        print("JSON parse hatası:", instruction_json)
        return None

    # --- doc_list -> DataFrame ---
    rows = []
    for d in doc_list:
        row = {}
        for part in d.get("text", "").split(" | "):
            if ": " in part:
                k, v = part.split(": ", 1)
                row[normalize_text(k)] = normalize_text(v)
        rows.append(row)

    df = pd.DataFrame(rows)

    # --- instruction parçaları ---
    target = instr.get("target")
    source = instr.get("source")
    op = instr.get("operation")
    target_filt = instr.get("target_filter")
    source_filt = instr.get("source_filter")
    mode = instr.get("mode", "seperate")
    extra_ops = instr.get("extra_operations", [])
    group_by = instr.get("group_by")

    # --- normalize target/source ---
    if isinstance(target, str):
        target = [normalize_text(target)]
    else:
        target = [normalize_text(t) for t in target] if target else []

    normalized_source = []
    if source:
        if isinstance(source, str):   # <-- düzeltme
            normalized_source = [normalize_text(source)]
        else:
            for s in source:
                if isinstance(s, str):
                    normalized_source.append(normalize_text(s))
                elif isinstance(s, (list, tuple)):
                    normalized_source.append([normalize_text(x) for x in s])
    source = normalized_source
    # normalized_source = []
    # if source:
    #     for s in source:
    #         if isinstance(s, str):
    #             normalized_source.append(normalize_text(s))
    #         elif isinstance(s, (list, tuple)):
    #             normalized_source.append([normalize_text(x) for x in s])
    # source = normalized_source
    
    df_target = apply_filter(df.copy(), target_filt)
    df_source = apply_filter(df.copy(), source_filt)
    if df_target.empty or (source and df_source.empty):
        print("Filtreleme sonrası veri boş kaldı!")
        return None

    # --- target numeric ---
    # valid_targets = [t for t in target if t in df_target.columns]
    # for col in valid_targets:
    #     df_target[col] = to_numeric_safe(df_target[col])

    # # --- source numeric ---
    # valid_sources = [s for s in source if s in df_source.columns]
    # for col in valid_sources:
    #     df_source[col] = to_numeric_safe(df_source[col])

       # --- target numeric ---
    valid_targets = [t for t in target if t in df_target.columns]
    if not valid_targets:
        print("Target kolon(lar) bulunamadı:", target)
        print("Mevcut kolonlar:", df_target.columns.tolist())
        return None
    for col in valid_targets:
        df_target[col] = to_numeric_safe(df_target[col])

    # --- source numeric ---
    # --- source numeric ---
    valid_sources = [s for s in source if s in df_source.columns]
    for col in valid_sources:
        df_source[col] = to_numeric_safe(df_source[col])
    if not valid_sources:
        print("Source kolon(lar) bulunamadı veya gerekli değil:", source)


    # --- 'together' toplu hesaplama (grup bazlı değilken) ---
    if mode == "together" and not instr.get("group_by"):
        # Tüm hedef kolonları tek toplamda birleştir
        t_sum = df_target[valid_targets].sum().sum() if valid_targets else 0
        # Tüm kaynak kolonları tek toplamda birleştir (varsa)
        s_sum = df_source[valid_sources].sum().sum() if valid_sources else None

        t_series = pd.Series([t_sum])
        s_series = pd.Series([s_sum]) if s_sum is not None else None

        main_val = apply_op(t_series, op, s_series, mode="together")
        total_result = {op: main_val}
        for e_op in extra_ops:
            total_result[e_op] = apply_op(t_series, e_op, s_series, mode="together")
        return {"total": total_result}


    # --- grup bazlı hesaplama ---
    if group_by:
        if isinstance(group_by, str):
            group_by_cols = [normalize_text(group_by)]
        else:
            group_by_cols = [normalize_text(g) for g in group_by]

        missing = [g for g in group_by_cols if g not in df_target.columns]
        if missing:
            print("Group_by kolon(lar) bulunamadı:", missing)
            return None

        # Grupları tespit et (hedef filtresine göre)
        unique_groups = df_target[group_by_cols].drop_duplicates()
        group_results = {}
        max_group = None
        max_value = None

        for _, grp_vals in unique_groups.iterrows():
            mask = pd.Series(True, index=df_target.index)
            for col in group_by_cols:
                mask &= (df_target[col] == grp_vals[col])
            t_group = df_target[mask]

            # Aynı grup değerleriyle source'u da filtrele
            if not df_source.empty:
                mask_s = pd.Series(True, index=df_source.index)
                for col in group_by_cols:
                    if col in df_source.columns:
                        mask_s &= (df_source[col] == grp_vals[col])
                s_group = df_source[mask_s]
            else:
                s_group = df_source

            # Hedef ve kaynak toplamlarını çıkar
            t_sum = t_group[valid_targets].sum().sum() if valid_targets else 0
            s_sum = s_group[valid_sources].sum().sum() if valid_sources else None

            t_series = pd.Series([t_sum])
            s_series = pd.Series([s_sum]) if s_sum is not None else None

            main_val = apply_op(t_series, op, s_series, mode="together")
            g_key = tuple(grp_vals[col] for col in group_by_cols)
            if len(g_key) == 1:
                g_key = g_key[0]

            g_result = {op: main_val}
            for e_op in extra_ops:
                g_result[e_op] = apply_op(t_series, e_op, s_series, mode="together")
            group_results[g_key] = g_result

            # Max'i ana op üzerinden takip et
            try:
                comp_val = float(main_val) if main_val is not None else None
            except Exception:
                comp_val = None
            if comp_val is not None and (max_value is None or comp_val > max_value):
                max_value = comp_val
                max_group = g_key

        return {
            "_group_by": group_by_cols,
            "_group_results": group_results,
            "_group_max": {"group": max_group, "value": max_value},
        }

    # --- hesaplama ---
    result = {}
    help_calc_diff(df_target, df_source, op, mode, extra_ops, valid_targets, valid_sources, result)
    return result

def help_calc_diff(df_target, df_source, op, mode, extra_ops, valid_targets, valid_sources, result):
    if len(valid_targets) == 1:
        t = valid_targets[0]
        s_series = df_source[valid_sources[0]] if valid_sources else None
        main_val = apply_op(df_target[t], op, s_series, mode=mode)
        t_result = {op: main_val}
        for e_op in extra_ops:
            t_result[e_op] = apply_op(df_target[t], e_op, s_series, mode=mode)
        result[t] = t_result
    else:
        i = 0
        for t in valid_targets:
            s_series = df_source[valid_sources[i]] if valid_sources else None
            i += 1
            t_result = {op: apply_op(df_target[t], op, s_series, mode=mode)}
            for e_op in extra_ops:
                t_result[e_op] = apply_op(df_target[t], e_op, s_series, mode=mode)
            result[t] = t_result