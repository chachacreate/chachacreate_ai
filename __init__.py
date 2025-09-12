# __init__.py (프로젝트 루트)
"""
Image Classification API
이미지 분류 및 가격 정보 제공 API
"""

__version__ = "1.0.0"
__author__ = "chachacreate"
__description__ = "AI 이미지 분류 및 가격 정보 제공 서비스"

# 주요 컴포넌트 import
from config import Settings
from services import AIClassifierService, DatabaseService, PriceService

__all__ = [
    "Settings",
    "AIClassifierService", 
    "DatabaseService",
    "PriceService"
]