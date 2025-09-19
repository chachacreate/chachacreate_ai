"""
Legacy API 연동 서비스
기존 시스템과의 통신을 담당하는 서비스
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from config.settings import Settings

class LegacyService:
    """Legacy API 연동 서비스"""
    
    def __init__(self, settings: Settings):
        """
        초기화
        
        Args:
            settings: 애플리케이션 설정 인스턴스
        """
        self.settings = settings
        self.legacy_config = settings.get_legacy_config()
        self.legacy_api_url = self.legacy_config.get("legacy_path")
        self.session = None
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """
        Legacy 서비스 초기화
        
        Returns:
            초기화 성공 여부
        """
        try:
            print(f"🔗 Legacy API 연결 확인: {self.legacy_api_url}")
            
            # HTTP 세션 생성
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # Legacy API 연결 테스트
            connection_test = await self._test_connection()
            
            if connection_test:
                self.is_initialized = True
                print("✅ Legacy API 연결 테스트 성공")
                return True
            else:
                print("❌ Legacy API 연결 테스트 실패")
                await self.cleanup()
                return False
                
        except Exception as e:
            print(f"❌ Legacy 서비스 초기화 실패: {str(e)}")
            await self.cleanup()
            return False
    
    async def _test_connection(self) -> bool:
        """
        Legacy API 연결 테스트
        
        Returns:
            연결 성공 여부
        """
        try:
            url = f"{self.legacy_api_url}/summary"
            headers = {"Content-Type": "application/json"}
            
            # 테스트용 간단한 요청
            async with self.session.post(url, json="폰케이스", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    # 응답 구조 확인
                    if result.get("status") == 200 and "data" in result:
                        print(f"📡 Legacy API 테스트 응답: 상품수 {result['data'].get('productCount', 0)}개")
                        return True
                    else:
                        print(f"❌ Legacy API 응답 형식 오류: {result}")
                        return False
                else:
                    print(f"❌ Legacy API HTTP 오류: {response.status}")
                    return False
                    
        except aiohttp.ClientError as e:
            print(f"❌ Legacy API 연결 오류: {str(e)}")
            return False
        except asyncio.TimeoutError:
            print(f"❌ Legacy API 연결 타임아웃")
            return False
        except Exception as e:
            print(f"❌ Legacy API 테스트 중 예상치 못한 오류: {str(e)}")
            return False
    
    async def cleanup(self):
        """리소스 정리"""
        if self.session and not self.session.closed:
            await self.session.close()
            print("🧹 Legacy 서비스 세션이 정리되었습니다.")
        
        self.is_initialized = False
    
    def is_connected(self) -> bool:
        """
        연결 상태 확인
        
        Returns:
            연결 상태
        """
        return (
            self.is_initialized and 
            self.session is not None and 
            not self.session.closed
        )
    
    async def call_legacy_api(self, endpoint: str, data: Any = None, method: str = "POST") -> Optional[Dict[str, Any]]:
        """
        Legacy API 호출 (범용)
        
        Args:
            endpoint: API 엔드포인트 (예: "/legacy/summary")
            data: 요청 데이터
            method: HTTP 메소드
            
        Returns:
            API 응답 딕셔너리 또는 None
        """
        if not self.is_connected():
            print("❌ Legacy 서비스가 연결되지 않았습니다.")
            return None
        
        try:
            url = f"{self.legacy_api_url}{endpoint}"
            headers = {"Content-Type": "application/json"}
            
            print(f"📡 Legacy API 호출: {method} {url}")
            if data:
                print(f"📦 요청 데이터: {data}")
            
            if method.upper() == "POST":
                async with self.session.post(url, json=data, headers=headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    return await self._handle_response(response)
            else:
                print(f"❌ 지원하지 않는 HTTP 메소드: {method}")
                return None
                
        except aiohttp.ClientError as e:
            print(f"❌ Legacy API 연결 오류: {str(e)}")
            return None
        except asyncio.TimeoutError:
            print(f"❌ Legacy API 호출 타임아웃: {endpoint}")
            return None
        except Exception as e:
            print(f"❌ Legacy API 호출 중 예상치 못한 오류: {str(e)}")
            return None
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Optional[Dict[str, Any]]:
        """
        Legacy API 응답 처리
        
        Args:
            response: aiohttp 응답 객체
            
        Returns:
            처리된 응답 딕셔너리 또는 None
        """
        if response.status == 200:
            try:
                result = await response.json()
                print(f"✅ Legacy API 응답 성공: 상태 {result.get('status', 'unknown')}")
                return result
            except Exception as e:
                print(f"❌ Legacy API 응답 파싱 오류: {str(e)}")
                return None
        else:
            try:
                error_text = await response.text()
                print(f"❌ Legacy API 호출 실패 - 상태코드: {response.status}")
                print(f"   응답: {error_text}")
            except:
                print(f"❌ Legacy API 호출 실패 - 상태코드: {response.status}")
            return None
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        연결 정보 반환
        
        Returns:
            연결 정보 딕셔너리
        """
        return {
            "legacy_api_url": self.legacy_api_url,
            "is_initialized": self.is_initialized,
            "is_connected": self.is_connected(),
            "session_active": self.session is not None and not self.session.closed,
            "legacy_path": self.legacy_config.get("legacy_path", ""),
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Legacy 서비스 헬스체크
        
        Returns:
            헬스체크 결과
        """
        if not self.is_connected():
            return {
                "healthy": False,
                "error": "Service not connected",
                "connection_info": self.get_connection_info()
            }
        
        # 실제 API 호출로 헬스체크
        try:
            result = await self.call_legacy_api("/summary", "폰케이스")
            
            if result and result.get("status") == 200:
                return {
                    "healthy": True,
                    "legacy_api_available": True,
                    "test_response": f"테스트 상품수: {result.get('data', {}).get('productCount', 0)}개",
                    "connection_info": self.get_connection_info()
                }
            else:
                return {
                    "healthy": False,
                    "legacy_api_available": False,
                    "error": "API call failed or invalid response",
                    "connection_info": self.get_connection_info()
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "legacy_api_available": False,
                "error": f"Health check failed: {str(e)}",
                "connection_info": self.get_connection_info()
            }