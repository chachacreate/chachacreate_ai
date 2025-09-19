"""
가격 정보 조회 및 분석 서비스
AI 카테고리 기반 상품 가격 통계 제공 (Legacy API 연동)
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from .legacy_service import LegacyService

class PriceService:
    """가격 정보 조회 및 분석 서비스 (Legacy API 기반)"""
    
    # AI 모델 카테고리와 Legacy API 카테고리 매핑 테이블
    AI_TO_LEGACY_CATEGORY_MAP = {
        "가방_파우치": "가방/파우치",
        "귀걸이": "귀걸이", 
        "꽃_식물": "꽃/식물",
        "노트_필기도구": "노트/필기도구",
        "반지": "반지",
        "생활한복": "생활한복",
        "여성신발_수제화": "여성신발/수제화",
        "인형_장난감": "인형/장난감",
        "조명": "조명",
        "주차번호_차량스티커": "주차번호/차량스티커",
        "티셔츠_니트_셔츠": "티셔츠/니트/셔츠",
        "팔찌": "팔찌",
        "패브릭": "패브릭",
        "폰케이스": "폰케이스"
    }
    
    def __init__(self, legacy_service: LegacyService):
        """
        초기화
        
        Args:
            legacy_service: Legacy API 서비스 인스턴스
        """
        self.legacy_service = legacy_service
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션 생성 또는 기존 세션 반환"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)  # 30초 타임아웃
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def cleanup(self):
        """리소스 정리"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def is_available(self) -> bool:
        """
        가격 서비스 사용 가능 여부 확인
        
        Returns:
            서비스 사용 가능 여부
        """
        return self.legacy_service is not None
    
    def get_legacy_category_name(self, ai_category: str) -> Optional[str]:
        """
        AI 카테고리를 Legacy API 카테고리명으로 변환
        
        Args:
            ai_category: AI 모델의 카테고리명
            
        Returns:
            Legacy API의 카테고리명 또는 None
        """
        return self.AI_TO_LEGACY_CATEGORY_MAP.get(ai_category)
    
    def get_all_category_mappings(self) -> Dict[str, str]:
        """
        모든 카테고리 매핑 정보 반환
        
        Returns:
            AI 카테고리 -> Legacy API 카테고리 매핑 딕셔너리
        """
        return self.AI_TO_LEGACY_CATEGORY_MAP.copy()
    
    async def get_category_price_range(self, category_name: str) -> Optional[Dict[str, Any]]:
        """
        카테고리별 상세 가격 통계 조회 (Legacy API 호출)
        
        Args:
            category_name: AI 모델의 카테고리명
            
        Returns:
            가격 통계 정보 딕셔너리 또는 None
        """
        if not self.is_available():
            print("❌ Legacy 서비스가 사용 불가능합니다.")
            return None
        
        legacy_category_name = self.get_legacy_category_name(category_name)
        if not legacy_category_name:
            print(f"❌ 카테고리 매핑을 찾을 수 없습니다: {category_name}")
            return None
        
        try:
            session = await self._get_session()
            
            # Legacy API 호출
            url = f"{self.legacy_service.legacy_api_url}/summary"
            headers = {"Content-Type": "application/json"}
            
            print(f"📡 Legacy API 호출: {url}")
            print(f"📦 요청 카테고리: {legacy_category_name}")
            
            async with session.post(url, json=legacy_category_name, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Legacy API 응답 구조 확인
                    if result.get("status") == 200 and "data" in result:
                        data = result["data"]
                        
                        # Legacy API 응답을 표준 형식으로 변환
                        price_stats = {
                            "average_price": float(data.get("avgPrice", 0)),
                            "min_price": float(data.get("minPrice", 0)),
                            "max_price": float(data.get("maxPrice", 0)),
                            "median_price": float(data.get("medianPrice", 0)),
                            "q1_price": float(data.get("q1Price", 0)),
                            "q3_price": float(data.get("q3Price", 0)),
                            "product_count": int(data.get("productCount", 0)),
                            "price_stddev": float(data.get("priceStddev", 0)),
                            "legacy_category": legacy_category_name,
                            "ai_category": category_name
                        }
                        
                        # 가격 범위 계산
                        price_stats["price_range"] = price_stats["max_price"] - price_stats["min_price"]
                        
                        print(f"📊 카테고리 '{legacy_category_name}' 가격 통계:")
                        print(f"   평균: {price_stats['average_price']:,.0f}원")
                        print(f"   범위: {price_stats['min_price']:,.0f}원 ~ {price_stats['max_price']:,.0f}원")
                        print(f"   중앙값: {price_stats['median_price']:,.0f}원")
                        print(f"   상품수: {price_stats['product_count']}개")
                        
                        return price_stats
                    else:
                        print(f"❌ Legacy API 응답 오류: {result.get('message', 'Unknown error')}")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ Legacy API 호출 실패 - 상태코드: {response.status}")
                    print(f"   응답: {error_text}")
                    return None
                    
        except aiohttp.ClientError as e:
            print(f"❌ Legacy API 연결 오류: {str(e)}")
            return None
        except asyncio.TimeoutError:
            print(f"❌ Legacy API 호출 타임아웃: {category_name}")
            return None
        except Exception as e:
            print(f"❌ Legacy API 호출 중 예상치 못한 오류: {str(e)}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Legacy API 상태 확인
        
        Returns:
            상태 정보 딕셔너리
        """
        try:
            session = await self._get_session()
            
            # Legacy API 헬스체크 (간단한 요청으로 테스트)
            url = f"{self.legacy_service.legacy_api_url}/summary"
            headers = {"Content-Type": "application/json"}
            
            async with session.post(url, json="폰케이스", headers=headers) as response:
                if response.status == 200:
                    return {
                        "legacy_api_available": True,
                        "legacy_api_url": self.legacy_service.legacy_api_url,
                        "status_code": response.status
                    }
                else:
                    return {
                        "legacy_api_available": False,
                        "legacy_api_url": self.legacy_service.legacy_api_url,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "legacy_api_available": False,
                "legacy_api_url": self.legacy_service.legacy_api_url,
                "error": str(e)
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        가격 서비스 상태 정보 반환
        
        Returns:
            서비스 상태 정보 딕셔너리
        """
        return {
            "is_available": self.is_available(),
            "legacy_service_connected": self.legacy_service is not None,
            "legacy_api_url": self.legacy_service.legacy_api_url if self.legacy_service else None,
            "supported_categories": len(self.AI_TO_LEGACY_CATEGORY_MAP),
            "category_mappings": self.AI_TO_LEGACY_CATEGORY_MAP,
            "session_active": self.session is not None and not self.session.closed
        }