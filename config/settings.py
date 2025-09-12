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
        "http://chachacreate.shinhanacademy.co.kr",
        "https://chachacreate.shinhanacademy.co.kr"
    ]
    
    # === AI 모델 설정 ===
    MODEL_PATH: str = "/path/to/your/model/best.pth"
    IMG_SIZE: int = 224
    IMAGENET_MEAN: List[float] = [0.485, 0.456, 0.406]
    IMAGENET_STD: List[float] = [0.229, 0.224, 0.225]
    
    # === Oracle 데이터베이스 설정 ===
    WALLET_PATH: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    WALLET_PASSWORD: str = ""
    ORACLE_SERVICE_NAME: str = ""
    
    # === 데이터베이스 연결 풀 설정 ===
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10
    DB_POOL_INCREMENT: int = 1
    
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
        
        # Oracle 설정
        self.WALLET_PATH = os.getenv("WALLET_PATH", self.WALLET_PATH)
        # TNS_ADMIN이 설정되어 있으면 WALLET_PATH보다 우선
        if os.getenv("TNS_ADMIN"):
            self.WALLET_PATH = os.getenv("TNS_ADMIN")
        
        self.DB_USER = os.getenv("DB_USER", self.DB_USER)
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", self.DB_PASSWORD)
        self.WALLET_PASSWORD = os.getenv("WALLET_PASSWORD", self.WALLET_PASSWORD)
        self.ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", self.ORACLE_SERVICE_NAME)
        
        # 연결 풀 설정
        self.DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", str(self.DB_POOL_MIN)))
        self.DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", str(self.DB_POOL_MAX)))
        self.DB_POOL_INCREMENT = int(os.getenv("DB_POOL_INCREMENT", str(self.DB_POOL_INCREMENT)))
        
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
        print(f"   Wallet 경로: {self.WALLET_PATH}")
        print(f"   DB 사용자: {self.DB_USER}")
        print(f"   Oracle 서비스: {self.ORACLE_SERVICE_NAME}")
        print(f"   서버: {self.HOST}:{self.PORT}")
    
    def _validate_paths(self):
        """경로 유효성 검증"""
        # Wallet 경로 존재 확인
        wallet_path = Path(self.WALLET_PATH)
        if not wallet_path.exists():
            print(f"⚠️ Wallet 경로가 존재하지 않습니다: {self.WALLET_PATH}")
        else:
            # 필수 wallet 파일들 확인
            required_files = ["tnsnames.ora", "sqlnet.ora"]
            missing_files = []
            for file_name in required_files:
                if not (wallet_path / file_name).exists():
                    missing_files.append(file_name)
            
            if missing_files:
                print(f"⚠️ 누락된 wallet 파일들: {', '.join(missing_files)}")
            else:
                print(f"✅ Wallet 파일들이 확인되었습니다: {self.WALLET_PATH}")
        
        # 모델 파일 존재 확인
        model_path = Path(self.MODEL_PATH)
        if not model_path.exists():
            print(f"⚠️ 모델 파일이 존재하지 않습니다: {self.MODEL_PATH}")
        else:
            print(f"✅ 모델 파일이 확인되었습니다: {self.MODEL_PATH}")
    
    def _validate_required_settings(self):
        """필수 설정값 검증 (모델 파일은 경고만)"""
        errors = []
        warnings = []
        
        if not self.ORACLE_SERVICE_NAME:
            errors.append("ORACLE_SERVICE_NAME이 설정되지 않았습니다.")
        
        if not Path(self.MODEL_PATH).exists():
            warnings.append(f"모델 파일이 존재하지 않습니다: {self.MODEL_PATH} (AI 기능 비활성화)")
            
        if not Path(self.WALLET_PATH).exists():
            warnings.append(f"Wallet 경로가 존재하지 않습니다: {self.WALLET_PATH} (DB 기능 비활성화)")
        
        # 경고 메시지 출력
        if warnings:
            print("⚠️ 경고:")
            for warning in warnings:
                print(f"   - {warning}")
        
        return errors
    
    def get_db_config(self) -> dict:
        """데이터베이스 연결 설정 반환"""
        return {
            "wallet_path": self.WALLET_PATH,
            "db_user": self.DB_USER,
            "db_password": self.DB_PASSWORD,
            "wallet_password": self.WALLET_PASSWORD,
            "service_name": self.ORACLE_SERVICE_NAME,
            "pool_min": self.DB_POOL_MIN,
            "pool_max": self.DB_POOL_MAX,
            "pool_increment": self.DB_POOL_INCREMENT
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
            검증 성공 여부
        """
        errors = self._validate_required_settings()
        
        if errors:
            print("❌ 설정 검증 실패:")
            for error in errors:
                print(f"   - {error}")
            print("\n💡 .env 파일을 확인하고 필요한 설정을 추가해주세요.")
            return False
        else:
            print("✅ 모든 설정이 유효합니다.")
            return True
    
    def __str__(self):
        """설정 정보 문자열 표현"""
        return f"""
Settings Configuration:
- Model Path: {self.MODEL_PATH}
- Wallet Path: {self.WALLET_PATH}
- Wallet User: {self.WALLET_USER}
- Oracle Service: {self.ORACLE_SERVICE_NAME}
- Server: {self.HOST}:{self.PORT} (workers: {self.WORKERS})
- DB Pool: {self.DB_POOL_MIN}-{self.DB_POOL_MAX}
- Categories: {len(self.CLASS_NAMES)} items
- CORS Origins: {len(self.ALLOWED_ORIGINS)} origins
        """.strip()