#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import datetime as dt
import json
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

try:
    import arcpy
except Exception:
    arcpy = None


DEFAULT_DEPT_OUT_NAME = "Livrables_Departements"
DEFAULT_DEPT_REPORT_JSON = "00_recap_regroupement_departements.json"
DEFAULT_DEPT_REPORT_TXT = "00_recap_regroupement_departements.txt"
EXCEL_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".xlsb"}
TECHNICAL_ZC_DIRS = {"JSON_ZC", "JSON_ZD", "MBTILES_ZD"}


def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str, level: str = "INFO") -> None:
    print(f"[{now_str()}] [{level}] {msg}")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def clear_directory(path: str) -> None:
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        child = os.path.join(path, name)
        if os.path.isdir(child):
            shutil.rmtree(child)
        else:
            os.remove(child)


def safe_name(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_\- ]+", "_", value or "")
    out = re.sub(r"\s+", "_", out).strip("_")
    return out or "INCONNU"


def list_zs_dirs(source_dir: str) -> List[str]:
    if not os.path.isdir(source_dir):
        return []
    out = []
    for name in sorted(os.listdir(source_dir)):
        path = os.path.join(source_dir, name)
        if os.path.isdir(path) and name.upper().startswith("ZS"):
            out.append(path)
    return out


def list_zc_dirs(zs_dir: str) -> List[str]:
    if not os.path.isdir(zs_dir):
        return []
    out = []
    for name in sorted(os.listdir(zs_dir)):
        path = os.path.join(zs_dir, name)
        if os.path.isdir(path) and name.upper().startswith("ZC"):
            out.append(path)
    return out


def _count_ext(folder_path: str, ext: str, recursive: bool = False) -> int:
    if not os.path.isdir(folder_path):
        return -1
    ext_l = ext.lower()
    total = 0

    if recursive:
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                if file_name.lower().endswith(ext_l):
                    total += 1
        return total

    for file_name in os.listdir(folder_path):
        child = os.path.join(folder_path, file_name)
        if os.path.isfile(child) and file_name.lower().endswith(ext_l):
            total += 1
    return total


def verify_zs_content(zs_dir: str) -> Dict[str, object]:
    """
    Vérifie une structure ZS et retourne une version corrigée utilisable:
    - garde uniquement les ZC valides (Json_ZC, Json_ZD, Mbtiles_ZD non vides)
    - exige au moins un JSON ZS à la racine
    """
    zs_name = os.path.basename(zs_dir)
    anomalies: List[str] = []
    valid_zc_dirs: List[str] = []

    zs_json_files = [
        os.path.join(zs_dir, name)
        for name in sorted(os.listdir(zs_dir))
        if os.path.isfile(os.path.join(zs_dir, name)) and name.lower().endswith(".json")
    ]
    if not zs_json_files:
        anomalies.append(f"{zs_name}: aucun JSON ZS à la racine")

    zc_dirs = list_zc_dirs(zs_dir)
    if not zc_dirs:
        anomalies.append(f"{zs_name}: aucun dossier ZC*")

    for zc_dir in zc_dirs:
        zc_name = os.path.basename(zc_dir)
        json_zc_dir = os.path.join(zc_dir, "Json_ZC")
        json_zd_dir = os.path.join(zc_dir, "Json_ZD")
        mbtiles_zd_dir = os.path.join(zc_dir, "Mbtiles_ZD")

        json_zc_count = _count_ext(json_zc_dir, ".json", recursive=True)
        json_zd_count = _count_ext(json_zd_dir, ".json", recursive=True)
        mbtiles_zd_count = _count_ext(mbtiles_zd_dir, ".mbtiles", recursive=True)

        local_errors = []
        if json_zc_count == -1:
            local_errors.append("dossier Json_ZC manquant")
        elif json_zc_count == 0:
            local_errors.append("Json_ZC vide")

        if json_zd_count == -1:
            local_errors.append("dossier Json_ZD manquant")
        elif json_zd_count == 0:
            local_errors.append("Json_ZD vide")

        if mbtiles_zd_count == -1:
            local_errors.append("dossier Mbtiles_ZD manquant")
        elif mbtiles_zd_count == 0:
            local_errors.append("Mbtiles_ZD vide")

        if local_errors:
            anomalies.append(f"{zs_name}/{zc_name}: " + "; ".join(local_errors))
            continue

        valid_zc_dirs.append(zc_dir)

    return {
        "zs_name": zs_name,
        "zs_json_files": zs_json_files,
        "zc_total": len(zc_dirs),
        "valid_zc_dirs": valid_zc_dirs,
        "valid_zc_count": len(valid_zc_dirs),
        "has_blocking_issue": (not zs_json_files) or (len(valid_zc_dirs) == 0),
        "anomalies": anomalies,
    }


def copy_files_to_dir(file_paths: List[str], destination_dir: str) -> Tuple[int, int]:
    copied = 0
    skipped = 0
    ensure_dir(destination_dir)

    for file_path in file_paths:
        destination_path = os.path.join(destination_dir, os.path.basename(file_path))
        if os.path.exists(destination_path):
            skipped += 1
            continue
        shutil.copy2(file_path, destination_path)
        copied += 1

    return copied, skipped


def copy_files_to_dir_with_names(file_destinations: List[Tuple[str, str]], destination_dir: str) -> Tuple[int, int]:
    copied = 0
    skipped = 0
    ensure_dir(destination_dir)

    for file_path, destination_name in file_destinations:
        destination_path = os.path.join(destination_dir, destination_name)
        if os.path.exists(destination_path):
            skipped += 1
            continue
        shutil.copy2(file_path, destination_path)
        copied += 1

    return copied, skipped


def extract_zs_digits(zs_code: str) -> str:
    text = (zs_code or "").upper().strip()
    if text.startswith("ZS"):
        text = text[2:]
    return re.sub(r"\D", "", text)


def extract_dept_code_from_zs(zs_code: str) -> Optional[str]:
    """
    Règle demandée:
      ZS080201 -> digits après préfixe ZS = 080201
      code département = les 2 chiffres après les 2 premiers = "02"
    """
    digits = extract_zs_digits(zs_code)
    if len(digits) < 4:
        return None
    return digits[2:4]


def detect_existing_field(fields: List[str], candidates: List[str]) -> Optional[str]:
    lowered = {f.lower(): f for f in fields}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def detect_dept_name_field(fields: List[str]) -> Optional[str]:
    candidates = [
        "Nom_DEP",
        "NOM_DEP",
        "nom_dep",
        "Nom_Departement",
        "NOM_DEPARTEMENT",
        "NomDepartement",
        "Departement",
        "DEPARTEMENT",
        "Nom_Depart",
        "NOM_DEPART",
        "Dept_Nom",
        "LIB_DEPARTEMENT",
    ]
    hit = detect_existing_field(fields, candidates)
    if hit:
        return hit

    for f in fields:
        lf = f.lower()
        if "depart" in lf and ("nom" in lf or "lib" in lf):
            return f
    return None


def normalize_dept_code(value: object) -> Optional[str]:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value).strip())
    if not digits:
        return None
    if len(digits) >= 2:
        return digits[-2:]
    return digits.zfill(2)


def load_dept_name_by_zs_seq(
    zc_fc: str,
    zc_zs_field_hint: str,
    dept_name_field: Optional[str],
) -> Tuple[Dict[int, str], Dict[str, str]]:
    """
    Lit la couche ZC et retourne:
    - dict {zs_seq_int: nom_dept}
      ou zs_seq_int = valeur entiere du champ ZS dans ZC
      (correspond aux 2 derniers chiffres du nom de dossier ZS, ex: ZS080107 -> 7)
    - metadata champs utilisés
    """
    if arcpy is None:
        raise RuntimeError("ArcPy indisponible. Utiliser l'environnement arcgispro-gdal.")

    if not arcpy.Exists(zc_fc):
        raise RuntimeError(f"Couche ZC introuvable: {zc_fc}")

    fields = [f.name for f in arcpy.ListFields(zc_fc)]

    zc_zs_field = detect_existing_field(fields, [zc_zs_field_hint, "Code_ZS", "ZS"])
    if not zc_zs_field:
        raise RuntimeError("Champ ZS introuvable dans la couche ZC")

    used_dept_name_field = dept_name_field if dept_name_field in fields else None
    if not used_dept_name_field:
        used_dept_name_field = detect_dept_name_field(fields)

    cursor_fields = [zc_zs_field]
    if used_dept_name_field and used_dept_name_field not in cursor_fields:
        cursor_fields.append(used_dept_name_field)

    # dict: zs_seq_int -> {nom_dep: count}
    zs_to_names: Dict[int, Dict[str, int]] = {}

    with arcpy.da.SearchCursor(zc_fc, cursor_fields) as cursor:
        for row in cursor:
            row_map = {cursor_fields[i]: row[i] for i in range(len(cursor_fields))}

            zs_value = row_map.get(zc_zs_field)
            if zs_value is None:
                continue
            try:
                zs_seq_int = int(zs_value)
            except (ValueError, TypeError):
                continue

            dept_name_raw = row_map.get(used_dept_name_field) if used_dept_name_field else None
            dept_name = str(dept_name_raw).strip() if dept_name_raw is not None else ""

            zs_to_names.setdefault(zs_seq_int, {})
            if dept_name:
                zs_to_names[zs_seq_int][dept_name] = zs_to_names[zs_seq_int].get(dept_name, 0) + 1

    # Conserver le nom le plus frequent pour chaque zs_seq_int
    zs_seq_to_name: Dict[int, str] = {}
    for zs_seq_int, names in zs_to_names.items():
        if names:
            sorted_names = sorted(names.items(), key=lambda kv: (-kv[1], kv[0]))
            zs_seq_to_name[zs_seq_int] = sorted_names[0][0]

    meta = {
        "zc_zs_field": zc_zs_field,
        "dept_code_field": "<derive_from_zs_folder_name>",
        "dept_name_field": used_dept_name_field or "<not_found>",
    }
    return zs_seq_to_name, meta


def list_commune_excel_files(zc_dir: str) -> List[Tuple[str, str]]:
    excel_files: List[Tuple[str, str]] = []

    if not os.path.isdir(zc_dir):
        return excel_files

    for child_name in sorted(os.listdir(zc_dir)):
        child_path = os.path.join(zc_dir, child_name)
        if not os.path.isdir(child_path):
            continue
        if child_name.upper() in TECHNICAL_ZC_DIRS:
            continue

        for root, _, files in os.walk(child_path):
            for file_name in sorted(files):
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in EXCEL_EXTENSIONS:
                    continue
                excel_files.append((child_path, os.path.join(root, file_name)))

    return excel_files


def build_flat_excel_destination_name(
    zs_name: str,
    zc_name: str,
    commune_dir: str,
    file_path: str,
) -> str:
    rel_path = os.path.relpath(file_path, commune_dir)
    rel_no_ext, ext = os.path.splitext(rel_path)
    parts = [zs_name, zc_name, os.path.basename(commune_dir), rel_no_ext.replace(os.sep, "_")]
    base_name = safe_name("_".join(part for part in parts if part))
    return f"{base_name}{ext.lower()}"


def copy_tree_merge(src: str, dst: str) -> Tuple[int, int]:
    copied = 0
    skipped = 0

    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_root = dst if rel == "." else os.path.join(dst, rel)
        ensure_dir(target_root)

        for file_name in files:
            src_file = os.path.join(root, file_name)
            dst_file = os.path.join(target_root, file_name)
            if os.path.exists(dst_file):
                skipped += 1
            else:
                shutil.copy2(src_file, dst_file)
                copied += 1

    return copied, skipped


def build_text_report(recap: Dict[str, object]) -> str:
    lines = []
    lines.append("=" * 88)
    lines.append("REGROUPEMENT LIVRABLES PAR DEPARTEMENT")
    lines.append("=" * 88)
    lines.append(f"Date: {now_str()}")
    lines.append(f"Source: {recap['source_dir']}")
    lines.append(f"Sortie: {recap['out_dir']}")
    lines.append(f"ZS traitees: {recap['summary']['zs_count']}")
    lines.append(f"Departements detectes: {recap['summary']['dept_count']}")
    lines.append(f"ZS avec anomalies: {recap['summary']['zs_with_anomalies']}")
    lines.append(f"ZS ignorees (bloquantes): {recap['summary']['zs_skipped']}")
    lines.append(f"ZC invalides ignorees: {recap['summary']['zc_invalid_skipped']}")
    lines.append(f"Fichiers copies: {recap['summary']['files_copied']}")
    lines.append(f"Fichiers ignores (deja presents): {recap['summary']['files_skipped']}")
    lines.append(f"Excels communes copies: {recap['summary']['excel_files_copied']}")
    lines.append(f"Excels communes ignores: {recap['summary']['excel_files_skipped']}")
    lines.append("")

    lines.append("Champs ZC utilises:")
    lines.append(f"  - ZS: {recap['fields']['zc_zs_field']}")
    lines.append(f"  - Code departement: {recap['fields']['dept_code_field']}")
    lines.append(f"  - Nom departement: {recap['fields']['dept_name_field']}")
    lines.append("")

    lines.append("Options:")
    lines.append(f"  - Copie excels communes: {'oui' if recap['options']['copy_commune_excels'] else 'non'}")
    lines.append("")

    lines.append("Detail par departement:")
    for dept in recap["departements"]:
        lines.append(
            f"  - DEP {dept['dept_code']} | {dept['dept_name']} | ZS={dept['zs_count']} | "
            f"copies={dept['files_copied']} | ignores={dept['files_skipped']} | "
            f"excels={dept['excel_files_copied']} | excels_ignores={dept['excel_files_skipped']}"
        )

    if recap.get("anomalies"):
        lines.append("")
        lines.append("Anomalies detectees:")
        for message in recap["anomalies"]:
            lines.append(f"  - {message}")

    lines.append("")
    lines.append("=" * 88)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regroupe les livrables ZS/ZC/ZD par departement a partir du code ZS et des noms issus de la couche ZC.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--source-dir", required=True, help="Dossier source contenant les dossiers ZS* (ex: Livrables_ZS_Province)")
    parser.add_argument("--zc-fc", required=True, help="Couche ZC (feature class) pour récupérer le nom du département")
    parser.add_argument("--out-dir", default=None, help="Dossier de sortie. Défaut: <parent-source>/Livrables_Departements")
    parser.add_argument("--zs-field", default="ZS", help="Champ ZS dans la couche ZC")
    parser.add_argument("--dept-name-field", default=None, help="Champ nom departement dans ZC (optionnel, auto-detection sinon)")
    parser.add_argument("--clean-out-dir", action="store_true", help="Supprime le contenu du dossier de sortie avant copie")
    parser.add_argument(
        "--copy-commune-excels",
        action="store_true",
        help="Recopie les fichiers Excel trouves dans les dossiers communes vers la racine du dossier departement",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source_dir = os.path.abspath(args.source_dir)
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"source-dir introuvable: {source_dir}")

    if args.out_dir:
        out_dir = os.path.abspath(args.out_dir)
    else:
        source_parent = os.path.dirname(source_dir.rstrip(os.sep))
        out_dir = os.path.join(source_parent, DEFAULT_DEPT_OUT_NAME)

    ensure_dir(out_dir)
    if args.clean_out_dir:
        log(f"Nettoyage du dossier sortie: {out_dir}")
        clear_directory(out_dir)
        ensure_dir(out_dir)

    log("Lecture de la couche ZC pour construire le référentiel départements")
    zs_seq_to_name, fields_meta = load_dept_name_by_zs_seq(
        zc_fc=args.zc_fc,
        zc_zs_field_hint=args.zs_field,
        dept_name_field=args.dept_name_field,
    )
    log(f"ZS séquences indexées depuis ZC: {len(zs_seq_to_name)}")

    zs_dirs = list_zs_dirs(source_dir)
    if not zs_dirs:
        raise RuntimeError("Aucun dossier ZS* trouvé dans source-dir")

    recap = {
        "source_dir": source_dir,
        "out_dir": out_dir,
        "fields": fields_meta,
        "options": {
            "copy_commune_excels": args.copy_commune_excels,
        },
        "anomalies": [],
        "departements": [],
        "summary": {
            "dept_count": 0,
            "zs_count": 0,
            "zs_with_anomalies": 0,
            "zs_skipped": 0,
            "zc_invalid_skipped": 0,
            "files_copied": 0,
            "files_skipped": 0,
            "excel_files_copied": 0,
            "excel_files_skipped": 0,
        },
    }

    dept_map: Dict[str, Dict[str, object]] = {}

    for zs_path in zs_dirs:
        zs_name = os.path.basename(zs_path)
        verification = verify_zs_content(zs_path)
        anomalies = verification["anomalies"]
        if anomalies:
            recap["summary"]["zs_with_anomalies"] += 1
            recap["anomalies"].extend(anomalies)
            for message in anomalies:
                log(message, "WARNING")

        recap["summary"]["zc_invalid_skipped"] += max(
            0,
            verification["zc_total"] - verification["valid_zc_count"],
        )

        if verification["has_blocking_issue"]:
            recap["summary"]["zs_skipped"] += 1
            log(f"ZS ignorée (anomalie bloquante): {zs_name}", "WARNING")
            continue

        dept_code = extract_dept_code_from_zs(zs_name)
        if not dept_code:
            log(f"ZS ignorée (code dept non extractible): {zs_name}", "WARNING")
            continue

        # Récupérer Nom_DEP via la séquence ZS (derniers chiffres du dossier ZS)
        zs_digits = extract_zs_digits(zs_name)  # ex: '080107' depuis 'ZS080107'
        zs_seq_int = int(zs_digits[-2:]) if len(zs_digits) >= 2 else None
        dept_name = (
            zs_seq_to_name.get(zs_seq_int, f"DEPARTEMENT_{dept_code}")
            if zs_seq_int is not None
            else f"DEPARTEMENT_{dept_code}"
        )
        dept_folder = f"DEP{dept_code}_{safe_name(dept_name)}"

        if dept_code not in dept_map:
            dept_map[dept_code] = {
                "dept_code": dept_code,
                "dept_name": dept_name,
                "dept_dir": os.path.join(out_dir, dept_folder),
                "zs_names": [],
                "files_copied": 0,
                "files_skipped": 0,
                "excel_files_copied": 0,
                "excel_files_skipped": 0,
            }

        dept_entry = dept_map[dept_code]
        target_zs_dir = os.path.join(dept_entry["dept_dir"], zs_name)
        ensure_dir(dept_entry["dept_dir"])

        copied_zs, skipped_zs = copy_files_to_dir(verification["zs_json_files"], target_zs_dir)
        copied = copied_zs
        skipped = skipped_zs

        for valid_zc_dir in verification["valid_zc_dirs"]:
            zc_name = os.path.basename(valid_zc_dir)
            target_zc_dir = os.path.join(target_zs_dir, zc_name)
            c_part, s_part = copy_tree_merge(valid_zc_dir, target_zc_dir)
            copied += c_part
            skipped += s_part

            if args.copy_commune_excels:
                excel_destinations = [
                    (
                        file_path,
                        build_flat_excel_destination_name(
                            zs_name=zs_name,
                            zc_name=zc_name,
                            commune_dir=commune_dir,
                            file_path=file_path,
                        ),
                    )
                    for commune_dir, file_path in list_commune_excel_files(valid_zc_dir)
                ]
                copied_excel, skipped_excel = copy_files_to_dir_with_names(
                    excel_destinations,
                    dept_entry["dept_dir"],
                )
                dept_entry["excel_files_copied"] += copied_excel
                dept_entry["excel_files_skipped"] += skipped_excel
                recap["summary"]["excel_files_copied"] += copied_excel
                recap["summary"]["excel_files_skipped"] += skipped_excel

                if copied_excel or skipped_excel:
                    log(
                        f"{zs_name}/{zc_name} -> excels communes copies={copied_excel} ignorés={skipped_excel}"
                    )

        dept_entry["zs_names"].append(zs_name)
        dept_entry["files_copied"] += copied
        dept_entry["files_skipped"] += skipped

        recap["summary"]["zs_count"] += 1
        recap["summary"]["files_copied"] += copied
        recap["summary"]["files_skipped"] += skipped

        log(f"{zs_name} -> DEP {dept_code} ({dept_name}) | copies={copied} ignores={skipped}")

    for dept_code in sorted(dept_map.keys()):
        dept_entry = dept_map[dept_code]
        recap["departements"].append(
            {
                "dept_code": dept_entry["dept_code"],
                "dept_name": dept_entry["dept_name"],
                "dept_dir": dept_entry["dept_dir"],
                "zs_count": len(dept_entry["zs_names"]),
                "zs_names": sorted(dept_entry["zs_names"]),
                "files_copied": dept_entry["files_copied"],
                "files_skipped": dept_entry["files_skipped"],
                "excel_files_copied": dept_entry["excel_files_copied"],
                "excel_files_skipped": dept_entry["excel_files_skipped"],
            }
        )

    recap["summary"]["dept_count"] = len(recap["departements"])

    json_path = os.path.join(out_dir, DEFAULT_DEPT_REPORT_JSON)
    txt_path = os.path.join(out_dir, DEFAULT_DEPT_REPORT_TXT)

    with open(json_path, "w", encoding="utf-8") as stream:
        json.dump(recap, stream, indent=2, ensure_ascii=False)

    with open(txt_path, "w", encoding="utf-8") as stream:
        stream.write(build_text_report(recap))

    log(f"Recap JSON écrit: {json_path}")
    log(f"Recap TXT écrit: {txt_path}")
    log(
        "Terminé - "
        f"departements={recap['summary']['dept_count']} | "
        f"zs={recap['summary']['zs_count']} | "
        f"copies={recap['summary']['files_copied']} | "
        f"ignores={recap['summary']['files_skipped']} | "
        f"excels={recap['summary']['excel_files_copied']} | "
        f"excels_ignores={recap['summary']['excel_files_skipped']}"
    )


if __name__ == "__main__":
    main()
