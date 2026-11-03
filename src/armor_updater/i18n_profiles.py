# =============================================================================
# ARMOR-UPDATER - Window texts for update profiles and signed tags: i18n_profiles.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The texts of the profile selector and of the "only signed tags" switch, in the eight languages. Merged into i18n.TRANSLATIONS (a test keeps the key sets of every language equal)."""
from __future__ import annotations

COPY: dict[str, dict[str, str]] = {
    "en": {
        "profile_label": "Profile",
        "profile_none": "No profile (all projects)",
        "profile_summary": "{description} Selected: {count}.",
        "profile_proposal": "The composition of the profiles is a proposal that has yet to be confirmed.",
        "profile_missing_warning": "Not found on this machine, skipped: {names}.",
        "profile_member_tip": "Include this project in the profile",
        "signed_tags_checkbox": "Only signed tags",
        "signed_tags_hint": "Install only a revision whose git tag is signed by a pinned key (off by default).",
    },
    "es": {
        "profile_label": "Perfil",
        "profile_none": "Sin perfil (todos los proyectos)",
        "profile_summary": "{description} Seleccionados: {count}.",
        "profile_proposal": "La composición de los perfiles es una propuesta pendiente de confirmar.",
        "profile_missing_warning": "No encontrados en este equipo, omitidos: {names}.",
        "profile_member_tip": "Incluir este proyecto en el perfil",
        "signed_tags_checkbox": "Solo etiquetas firmadas",
        "signed_tags_hint": "Instala solo una revisión cuya etiqueta de git esté firmada por una clave fijada (apagado por defecto).",
    },
    "de": {
        "profile_label": "Profil",
        "profile_none": "Kein Profil (alle Projekte)",
        "profile_summary": "{description} Ausgewählt: {count}.",
        "profile_proposal": "Die Zusammensetzung der Profile ist ein Vorschlag, der noch bestätigt werden muss.",
        "profile_missing_warning": "Auf diesem Rechner nicht gefunden, übersprungen: {names}.",
        "profile_member_tip": "Dieses Projekt in das Profil aufnehmen",
        "signed_tags_checkbox": "Nur signierte Tags",
        "signed_tags_hint": "Nur eine Revision installieren, deren Git-Tag mit einem festgelegten Schlüssel signiert ist (standardmäßig aus).",
    },
    "fr": {
        "profile_label": "Profil",
        "profile_none": "Aucun profil (tous les projets)",
        "profile_summary": "{description} Sélectionnés : {count}.",
        "profile_proposal": "La composition des profils est une proposition qui reste à confirmer.",
        "profile_missing_warning": "Introuvables sur cette machine, ignorés : {names}.",
        "profile_member_tip": "Inclure ce projet dans le profil",
        "signed_tags_checkbox": "Seulement les étiquettes signées",
        "signed_tags_hint": "N'installer qu'une révision dont l'étiquette git est signée par une clé épinglée (désactivé par défaut).",
    },
    "it": {
        "profile_label": "Profilo",
        "profile_none": "Nessun profilo (tutti i progetti)",
        "profile_summary": "{description} Selezionati: {count}.",
        "profile_proposal": "La composizione dei profili è una proposta ancora da confermare.",
        "profile_missing_warning": "Non trovati su questa macchina, saltati: {names}.",
        "profile_member_tip": "Includi questo progetto nel profilo",
        "signed_tags_checkbox": "Solo tag firmati",
        "signed_tags_hint": "Installa solo una revisione il cui tag git è firmato da una chiave fissata (disattivato per impostazione predefinita).",
    },
    "ja": {
        "profile_label": "プロファイル",
        "profile_none": "プロファイルなし（すべてのプロジェクト）",
        "profile_summary": "{description} 選択中：{count}。",
        "profile_proposal": "プロファイルの構成は提案であり、まだ確認されていません。",
        "profile_missing_warning": "このマシンに見つからないためスキップしました：{names}。",
        "profile_member_tip": "このプロジェクトをプロファイルに含める",
        "signed_tags_checkbox": "署名付きタグのみ",
        "signed_tags_hint": "git タグが固定された鍵で署名されたリビジョンだけをインストールします（初期状態ではオフ）。",
    },
    "zh": {
        "profile_label": "配置文件",
        "profile_none": "无配置文件（所有项目）",
        "profile_summary": "{description} 已选择：{count}。",
        "profile_proposal": "配置文件的组成只是提议，仍有待确认。",
        "profile_missing_warning": "此机器上未找到，已跳过：{names}。",
        "profile_member_tip": "将此项目纳入配置文件",
        "signed_tags_checkbox": "仅限已签名标签",
        "signed_tags_hint": "只安装其 git 标签由固定密钥签名的修订（默认关闭）。",
    },
    "pt": {
        "profile_label": "Perfil",
        "profile_none": "Sem perfil (todos os projetos)",
        "profile_summary": "{description} Selecionados: {count}.",
        "profile_proposal": "A composição dos perfis é uma proposta que ainda tem de ser confirmada.",
        "profile_missing_warning": "Não encontrados neste computador, ignorados: {names}.",
        "profile_member_tip": "Incluir este projeto no perfil",
        "signed_tags_checkbox": "Só etiquetas assinadas",
        "signed_tags_hint": "Instala apenas uma revisão cuja etiqueta git esteja assinada por uma chave fixada (desligado por predefinição).",
    },
}
