"""
AI 이미지 분류 서비스
PyTorch 기반 ResNet18 모델을 사용한 이미지 분류
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms as T
from torchvision.models import resnet18
from PIL import Image
import numpy as np
import io
import cv2
from typing import List, Dict, Any
from pathlib import Path

from config.settings import Settings

class AIClassifierService:
    """AI 이미지 분류 서비스"""
    
    def __init__(self, model_path: str):
        """
        초기화
        
        Args:
            model_path: 학습된 모델 파일 경로
        """
        self.model_path = model_path
        self.model = None
        self.device = None
        self.settings = Settings()
        self._is_loaded = False
        self._setup_transform()
    
    def _setup_transform(self):
        """이미지 전처리 변환 파이프라인 설정"""
        self.transform = T.Compose([
            T.Resize(int(self.settings.IMG_SIZE * 1.15)),
            T.CenterCrop(self.settings.IMG_SIZE),
            T.ToTensor(),
            T.Normalize(
                mean=self.settings.IMAGENET_MEAN, 
                std=self.settings.IMAGENET_STD
            ),
        ])
        print("✅ 이미지 전처리 파이프라인이 설정되었습니다.")
    
    async def load_model(self) -> bool:
        """
        모델 로드 및 초기화
        
        Returns:
            로드 성공 여부
        """
        try:
            # 모델 파일 존재 확인
            if not Path(self.model_path).exists():
                print(f"❌ 모델 파일이 존재하지 않습니다: {self.model_path}")
                return False
            
            # 디바이스 설정
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"🔧 사용 디바이스: {self.device}")
            
            # 모델 아키텍처 생성
            self.model = resnet18(weights=None)
            self.model.fc = nn.Linear(512, len(self.settings.CLASS_NAMES))
            
            # 체크포인트 로드
            print(f"📥 모델 로딩 중: {self.model_path}")
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 상태 딕셔너리 로드
            state_dict = checkpoint.get("model", checkpoint)
            self.model.load_state_dict(state_dict, strict=True)
            
            # 모델을 디바이스로 이동 및 평가 모드 설정
            self.model = self.model.to(self.device)
            self.model.eval()
            
            self._is_loaded = True
            print(f"✅ AI 모델이 성공적으로 로드되었습니다 ({self.device})")
            return True
            
        except Exception as e:
            print(f"❌ 모델 로드 실패: {str(e)}")
            self._is_loaded = False
            return False
    
    def is_loaded(self) -> bool:
        """
        모델 로드 상태 확인
        
        Returns:
            로드 상태
        """
        return self._is_loaded and self.model is not None
    
    def get_categories(self) -> List[str]:
        """
        사용 가능한 카테고리 목록 반환
        
        Returns:
            카테고리 리스트
        """
        return self.settings.CLASS_NAMES.copy()
    
    def _safe_open_image_to_pil(self, image_bytes: bytes) -> Image.Image:
        """
        이미지 바이트를 PIL Image로 안전하게 변환
        
        Args:
            image_bytes: 이미지 바이트 데이터
            
        Returns:
            PIL Image 객체
            
        Raises:
            ValueError: 이미지 디코딩 실패시
        """
        try:
            # PIL로 먼저 시도
            with io.BytesIO(image_bytes) as img_buffer:
                img = Image.open(img_buffer).convert("RGB")
                # 이미지 유효성 검증
                img.load()
                return img
                
        except Exception as pil_error:
            print(f"PIL 로딩 실패, OpenCV로 시도: {pil_error}")
            
            try:
                # OpenCV fallback
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise ValueError("OpenCV로도 이미지를 디코딩할 수 없습니다.")
                
                # BGR to RGB 변환
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                return Image.fromarray(img_rgb)
                
            except Exception as cv_error:
                raise ValueError(f"이미지 디코딩 실패 (PIL: {pil_error}, OpenCV: {cv_error})")
    
    async def predict(self, image_bytes: bytes, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        이미지 분류 예측 수행
        
        Args:
            image_bytes: 이미지 바이트 데이터
            top_k: 반환할 상위 예측 개수
            
        Returns:
            예측 결과 리스트
            
        Raises:
            RuntimeError: 모델이 로드되지 않았거나 예측 실패시
        """
        if not self.is_loaded():
            raise RuntimeError("모델이 로드되지 않았습니다.")
        
        if top_k > len(self.settings.CLASS_NAMES):
            top_k = len(self.settings.CLASS_NAMES)
        
        try:
            # 이미지 전처리
            image = self._safe_open_image_to_pil(image_bytes)
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            print(f"🔍 이미지 분류 시작 (입력 크기: {input_tensor.shape})")
            
            # 예측 수행
            with torch.no_grad():
                # Forward pass
                logits = self.model(input_tensor)
                probabilities = F.softmax(logits, dim=1)
                
                # Top-K 결과 추출
                topk_prob, topk_idx = torch.topk(probabilities, top_k, dim=1)
                
                # 결과 구성
                predictions = []
                for i in range(top_k):
                    idx = topk_idx[0][i].item()
                    prob = topk_prob[0][i].item()
                    category_name = self.settings.CLASS_NAMES[idx]
                    
                    predictions.append({
                        "category": category_name,
                        "confidence": round(prob, 4),
                        "category_id": idx
                    })
                
                # 로그 출력
                top_prediction = predictions[0]
                print(f"🎯 예측 완료: {top_prediction['category']} "
                      f"(신뢰도: {top_prediction['confidence']:.2%})")
                
                return predictions
                
        except Exception as e:
            error_msg = f"이미지 분류 중 오류 발생: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        모델 정보 반환
        
        Returns:
            모델 정보 딕셔너리
        """
        return {
            "model_path": self.model_path,
            "device": str(self.device) if self.device else None,
            "is_loaded": self.is_loaded(),
            "num_classes": len(self.settings.CLASS_NAMES),
            "categories": self.settings.CLASS_NAMES,
            "input_size": self.settings.IMG_SIZE
        }