"""
애플리케이션 설정 관리
환경변수와 기본값을 통한 설정 관리
"""

import os
from typing import List
from pathlib import Path

class Settings:
    """애플리케이션 전역 설정 클래스"""
    
    # === API 설정 ===
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://chachacreate.shinhanacademy.co.kr",
        "https://chachacreate.shinhanacademy.co.kr"
    ]
    
    # === AI 모델 설정 ===
    MODEL_PATH: str = "./ckpt/best.pth"
    IMG_SIZE: int = 224
    IMAGENET_MEAN: List[float] = [0.485, 0.456, 0.406]
    IMAGENET_STD: List[float] = [0.229, 0.224, 0.225]
    
    # === Legacy API 설정 ===
    LEGACY_PATH: str = "http://localhost:9999/legacy"
    
    # === 서버 설정 ===
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    WORKERS: int = 2
    
    # === AI 모델 카테고리 ===
    CLASS_NAMES: List[str] = [
        "가방_파우치", "귀걸이", "꽃_식물", "노트_필기도구", 
        "반지", "생활한복", "여성신발_수제화", "인형_장난감", 
        "조명", "주차번호_차량스티커", "티셔츠_니트_셔츠", 
        "팔찌", "패브릭", "폰케이스"
    ]
    
    # === 로깅 설정 ===
    LOG_LEVEL: str = "INFO"
    
    def __init__(self):
        """환경변수에서 설정값 로드"""
        self._load_dotenv()
        self._load_from_env()
        self._validate_paths()
    
    def _load_dotenv(self):
        """
        .env 파일에서 환경변수 로드
        python-dotenv가 설치되어 있으면 사용, 없으면 수동으로 로드
        """
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ .env 파일이 로드되었습니다.")
        except ImportError:
            # python-dotenv가 없으면 수동으로 .env 파일 읽기
            env_path = Path('.env')
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                print("✅ .env 파일이 수동으로 로드되었습니다.")
            else:
                print("⚠️ .env 파일이 없습니다. 환경변수나 기본값을 사용합니다.")
    
    def _load_from_env(self):
        """환경변수에서 설정값 로드"""
        # 모델 경로
        self.MODEL_PATH = os.getenv("MODEL_PATH", self.MODEL_PATH)
        
        # Legacy API 설정
        self.LEGACY_PATH = os.getenv("LEGACY_PATH", self.LEGACY_PATH)
        
        # 서버 설정
        self.HOST = os.getenv("HOST", self.HOST)
        self.PORT = int(os.getenv("PORT", str(self.PORT)))
        self.WORKERS = int(os.getenv("WORKERS", str(self.WORKERS)))
        
        # 로깅 설정
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", self.LOG_LEVEL)
        
        # CORS 설정 (환경변수에서 쉼표로 구분된 값 로드)
        cors_origins = os.getenv("ALLOWED_ORIGINS")
        if cors_origins:
            self.ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
        
        print(f"🔧 설정 로드 완료:")
        print(f"   모델 경로: {self.MODEL_PATH}")
        print(f"   Legacy API: {self.LEGACY_PATH}")
        print(f"   서버: {self.HOST}:{self.PORT}")
        print(f"   CORS 허용: {', '.join(self.ALLOWED_ORIGINS)}")
    
    def _validate_paths(self):
        """경로 유효성 검증"""
        # 모델 파일 존재 확인
        model_path = Path(self.MODEL_PATH)
        if not model_path.exists():
            print(f"⚠️ 모델 파일이 존재하지 않습니다: {self.MODEL_PATH}")
        else:
            print(f"✅ 모델 파일이 확인되었습니다: {self.MODEL_PATH}")
        
        # Legacy API URL 형식 확인
        if not self.LEGACY_PATH.startswith(('http://', 'https://')):
            print(f"⚠️ Legacy API URL 형식이 올바르지 않습니다: {self.LEGACY_PATH}")
        else:
            print(f"✅ Legacy API URL이 확인되었습니다: {self.LEGACY_PATH}")
    
    def _validate_required_settings(self):
        """필수 설정값 검증"""
        errors = []
        warnings = []
        
        # 모델 파일 체크 (경고만)
        if not Path(self.MODEL_PATH).exists():
            warnings.append(f"모델 파일이 존재하지 않습니다: {self.MODEL_PATH} (AI 기능 비활성화)")
        
        # Legacy API URL 체크 (경고만)
        if not self.LEGACY_PATH.startswith(('http://', 'https://')):
            warnings.append(f"Legacy API URL 형식이 올바르지 않습니다: {self.LEGACY_PATH}")
        
        # 서버 설정 체크
        if not (1 <= self.PORT <= 65535):
            errors.append(f"포트 번호가 유효하지 않습니다: {self.PORT}")
        
        if self.WORKERS < 1:
            errors.append(f"워커 수가 유효하지 않습니다: {self.WORKERS}")
        
        # 경고 메시지 출력
        if warnings:
            print("⚠️ 경고:")
            for warning in warnings:
                print(f"   - {warning}")
        
        return errors
    
    def get_legacy_config(self) -> dict:
        """Legacy API 연결 설정 반환"""
        return {
            "legacy_path": self.LEGACY_PATH,
        }
    
    def get_server_config(self) -> dict:
        """서버 설정 반환"""
        return {
            "host": self.HOST,
            "port": self.PORT,
            "workers": self.WORKERS,
            "log_level": self.LOG_LEVEL.lower()
        }
    
    def validate_all(self) -> bool:
        """
        모든 설정 검증
        
        Returns:
            검증 성공 여부 (심각한 오류가 없으면 True)
        """
        errors = self._validate_required_settings()
        
        if errors:
            print("❌ 설정 검증 실패:")
            for error in errors:
                print(f"   - {error}")
            print("\n💡 .env 파일을 확인하고 필요한 설정을 추가해주세요.")
            return False
        else:
            print("✅ 핵심 설정이 유효합니다.")
            return True
    
    def __str__(self):
        """설정 정보 문자열 표현"""
        return f"""
Settings Configuration:
- Model Path: {self.MODEL_PATH}
- Legacy API: {self.LEGACY_PATH}
- Server: {self.HOST}:{self.PORT} (workers: {self.WORKERS})
- Categories: {len(self.CLASS_NAMES)} items
- CORS Origins: {len(self.ALLOWED_ORIGINS)} origins
        """.strip()