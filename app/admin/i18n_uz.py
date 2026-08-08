"""Uzbek (uz) localisation for starlette-admin.

starlette-admin ships catalogs for de/en/fr/ru/tr only. This module registers
a runtime ``uz`` locale: a babel translations object backed by the ``UZ`` dict
(for all Jinja/Python ``gettext`` strings) plus an ``i18n/dt/uz.json`` catalog
for the DataTables chrome (written into starlette-admin's statics at startup).

Call :func:`install_uzbek` once, before constructing ``Admin(...)``.
"""
import json
import logging
import pathlib
import shutil

logger = logging.getLogger(__name__)

# ── Jinja / Python gettext strings ─────────────────────────────────────
UZ = {
    "Actions": "Amallar",
    "Add item": "Element qo'shish",
    "Admin": "Boshqaruv",
    "Are you sure you want to delete this item?": "Ushbu elementni o'chirmoqchimisiz?",
    "Attribute": "Maydon",
    "Cancel": "Bekor qilish",
    "Create": "Yaratish",
    "Delete": "O'chirish",
    "Detail": "Batafsil",
    "Edit": "Tahrirlash",
    "Edit %(name)s": "%(name)s — tahrirlash",
    "Home": "Bosh sahifa",
    "Loading": "Yuklanmoqda",
    "Login to your account": "Hisobingizga kiring",
    "Logout": "Chiqish",
    "New": "Yangi",
    "New %(name)s": "Yangi %(name)s",
    "Oops… You just found an error page": "Voy… Xatolik yuz berdi",
    "Password": "Parol",
    "Search": "Qidirish",
    "Select a %(label)s": "%(label)s tanlang",
    "Check this to delete the current content of this field": "Joriy fayl mazmunini o'chirish uchun belgilang",
    "Remember me": "Meni eslab qol",
    "Save": "Saqlash",
    "Save and add another": "Saqlash va yana qo'shish",
    "Save and continue editing": "Saqlash va tahrirni davom ettirish",
    "Sign in": "Kirish",
    "Take me home": "Bosh sahifaga qaytish",
    "Username": "Foydalanuvchi nomi",
    "Value": "Qiymat",
    "With selected": "Tanlanganlar bilan",
    "Yes, Proceed": "Ha, davom etish",
    "Yes, delete": "Ha, o'chirish",
    # flash / status messages (Python side)
    "Item was successfully deleted": "Element muvaffaqiyatli o'chirildi",
    "%(count)d items were successfully deleted": "%(count)d ta element muvaffaqiyatli o'chirildi",
    "Item was successfully created": "Element muvaffaqiyatli yaratildi",
    "Item was successfully updated": "Element muvaffaqiyatli yangilandi",
}

# ── DataTables language catalog (uz) ───────────────────────────────────
DT_UZ = {
    "emptyTable": "Jadvalda ma'lumot yo'q",
    "info": "_TOTAL_ tadan _START_–_END_ ko'rsatilmoqda",
    "infoEmpty": "0 tadan 0–0 ko'rsatilmoqda",
    "infoFiltered": "(_MAX_ tadan filtrlangan)",
    "lengthMenu": "_MENU_ ta ko'rsatish",
    "loadingRecords": "Yuklanmoqda...",
    "processing": "Bajarilmoqda...",
    "search": "Qidirish:",
    "zeroRecords": "Mos yozuv topilmadi",
    "thousands": " ",
    "paginate": {
        "first": "Birinchi",
        "last": "Oxirgi",
        "next": "Keyingi",
        "previous": "Oldingi",
    },
    "buttons": {
        "colvis": "Ustunlar",
        "colvisRestore": "Ko'rinishni tiklash",
        "copy": "Nusxa olish",
        "csv": "CSV",
        "excel": "Excel",
        "pdf": "PDF",
        "print": "Chop etish",
        "pageLength": {"-1": "Barcha qatorlar", "_": "%d ta qator"},
    },
    "select": {
        "rows": {"1": "1 ta qator tanlandi", "_": "%d ta qator tanlandi"},
        "columns": {"1": "1 ta ustun tanlandi", "_": "%d ta ustun tanlandi"},
        "cells": {"1": "1 ta katak tanlandi", "_": "%d ta katak tanlandi"},
    },
    "searchBuilder": {
        "add": "Shart qo'shish",
        "button": {
            "0": "<i class=\"fa-solid fa-filter\"></i> Filtr",
            "_": "<i class=\"fa-solid fa-filter\"></i> Filtr (%d)",
        },
        "clearAll": "Tozalash",
        "condition": "Shart",
        "data": "Maydon",
        "deleteTitle": "Filtr shartini o'chirish",
        "logicAnd": "VA",
        "logicOr": "YOKI",
        "title": {"0": "Filtr", "_": "Filtr (%d)"},
        "value": "Qiymat",
        "conditions": {
            "string": {
                "contains": "Ichida bor",
                "empty": "Bo'sh",
                "endsWith": "Bilan tugaydi",
                "equals": "Teng",
                "not": "Emas",
                "notContains": "Ichida yo'q",
                "notEmpty": "Bo'sh emas",
                "startsWith": "Bilan boshlanadi",
            },
            "number": {
                "between": "Oraliqda",
                "empty": "Bo'sh",
                "equals": "Teng",
                "gt": "Katta",
                "gte": "Katta yoki teng",
                "lt": "Kichik",
                "lte": "Kichik yoki teng",
                "not": "Emas",
                "notEmpty": "Bo'sh emas",
            },
            "date": {
                "after": "Keyin",
                "before": "Oldin",
                "between": "Oraliqda",
                "empty": "Bo'sh",
                "equals": "Teng",
                "not": "Emas",
                "notEmpty": "Bo'sh emas",
            },
        },
    },
    "starlette-admin": {
        "buttons": {"export": "Eksport"},
        "conditions": {
            "empty": "Bo'sh",
            "false": "Yo'q",
            "notEmpty": "Bo'sh emas",
            "true": "Ha",
        },
    },
}


def install_uzbek() -> None:
    """Register the ``uz`` locale into starlette-admin (idempotent)."""
    try:
        from babel.support import NullTranslations

        import starlette_admin.i18n as sa_i18n
    except Exception as e:  # noqa: BLE001 — babel missing → keep default locale
        logger.warning("Uzbek admin locale not installed (%s)", e)
        return

    class _UzTranslations(NullTranslations):
        def ugettext(self, message):
            return UZ.get(message, message)

        gettext = ugettext

        def ungettext(self, singular, plural, n):
            key = singular if n == 1 else plural
            return UZ.get(key, key)

        ngettext = ungettext

    sa_i18n.translations["uz"] = _UzTranslations()
    if "uz" not in sa_i18n.SUPPORTED_LOCALES:
        sa_i18n.SUPPORTED_LOCALES.append("uz")

    # DataTables + momentjs assets live under starlette-admin's statics.
    import starlette_admin

    i18n_dir = pathlib.Path(starlette_admin.__file__).parent / "statics" / "i18n"
    dt_dir = i18n_dir / "dt"
    try:
        dt_dir.mkdir(parents=True, exist_ok=True)
        (dt_dir / "uz.json").write_text(
            json.dumps(DT_UZ, ensure_ascii=False), encoding="utf-8"
        )
        # avoid a 404 on momentjs/uz.js — starlette-admin's list.html always
        # requests `momentjs/<locale>.js`. This build ships only de/fr/ru/tr
        # (no en.js), so we can't copy the English calendar. Write a small
        # `uz` locale stub instead: `defineLocale('uz', {})` inherits moment's
        # built-in English defaults, so dates render fine and the 404 is gone.
        moment_dir = i18n_dir / "momentjs"
        moment_uz = moment_dir / "uz.js"
        if moment_dir.is_dir() and not moment_uz.is_file():
            moment_en = moment_dir / "en.js"
            if moment_en.is_file():
                shutil.copyfile(moment_en, moment_uz)
            else:
                moment_uz.write_text(
                    "(function(){if(typeof moment!=='undefined'){"
                    "moment.defineLocale('uz',{});}})();",
                    encoding="utf-8",
                )
    except OSError as e:  # noqa: BLE001
        logger.warning("Could not write uz i18n assets: %s", e)

    logger.info("✅ Uzbek admin locale registered")
