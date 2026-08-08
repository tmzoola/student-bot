"""18+ (NSFW) aniqlagich — profil rasmi (NudeNet, lokal) va bio matni.

NudeDetector og'ir (onnxruntime + opencv), shuning uchun faqat guard boti
uni chaqirganda dangasa (lazy) yuklanadi — web ilova bu modulni import qilmaydi.
"""
import logging

logger = logging.getLogger(__name__)

# Faqat ochiq (exposed) klasslar 18+ deb hisoblanadi — kiyimli klasslar emas.
_EXPOSED_CLASSES = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
}

_BIO_KEYWORDS = [
    "18+", "🔞", "onlyfans", "escort", "эскорт", "интим", "intim",
    "секс", "seks", "porn", "порно", "xxx", "nude", "vip video",
    "приват", "privat", "webcam", "camgirl", "sugar",
]

_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        from nudenet import NudeDetector
        _detector = NudeDetector()
    return _detector


def image_nsfw_score(image_path: str, threshold: float) -> float:
    """Rasmda 18+ kontent bo'lsa eng yuqori ishonch darajasini qaytaradi, aks holda 0.0."""
    detections = _get_detector().detect(image_path)
    scores = [
        d["score"]
        for d in detections
        if d["class"] in _EXPOSED_CLASSES and d["score"] >= threshold
    ]
    return max(scores) if scores else 0.0


def bio_flagged_words(bio: str | None) -> list[str]:
    """Bio ichidan topilgan shubhali kalit so'zlar ro'yxatini qaytaradi."""
    if not bio:
        return []
    low = bio.lower()
    return [kw for kw in _BIO_KEYWORDS if kw in low]
