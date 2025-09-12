"""
Oracle 공식 문서 방법 적용
config_dir와 wallet_location 파라미터 사용
"""

import os
import oracledb
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
from pathlib import Path

from config.settings import Settings

class DatabaseService:
    """Oracle 데이터베이스 연결 서비스 (공식 방법)"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection_pool = None
        self._is_connected = False
    
    async def initialize(self) -> bool:
        """Oracle 공식 문서 방법으로 연결"""
        try:
            wallet_path = Path(self.settings.WALLET_PATH)
            if not wallet_path.exists():
                print(f"Wallet 경로가 존재하지 않습니다: {self.settings.WALLET_PATH}")
                return False
            
            abs_wallet_path = str(wallet_path.absolute())
            print(f"Wallet 경로: {abs_wallet_path}")
            
            # 필수 파일 확인
            required_files = ["tnsnames.ora", "sqlnet.ora", "cwallet.sso"]
            for file_name in required_files:
                if not (wallet_path / file_name).exists():
                    print(f"{file_name} 파일이 없습니다")
                    return False
                else:
                    print(f"✓ {file_name}")
            
            db_config = self.settings.get_db_config()
            
            # Oracle 공식 방법: config_dir + wallet_location 사용
            try:
                print("Oracle 공식 방법 (config_dir + wallet_location)")
                
                # 단일 연결로 먼저 테스트
                test_conn = oracledb.connect(
                    config_dir=abs_wallet_path,
                    user=db_config['db_user'],
                    password=db_config['db_password'],
                    dsn=db_config['service_name'],
                    wallet_location=abs_wallet_path,
                    wallet_password=db_config.get('wallet_password', "")
                )
                
                # 연결 테스트
                cursor = test_conn.cursor()
                cursor.execute("SELECT 'Oracle Official Method Test' FROM DUAL")
                result = cursor.fetchone()
                cursor.close()
                test_conn.close()
                
                print(f"단일 연결 테스트 성공: {result[0]}")
                
                # 성공했으므로 연결 풀 생성
                self.connection_pool = oracledb.create_pool(
                    config_dir=abs_wallet_path,
                    user=db_config['db_user'],
                    password=db_config['db_password'],
                    dsn=db_config['service_name'],
                    wallet_location=abs_wallet_path,
                    wallet_password=db_config.get('wallet_password', ""),
                    min=db_config['pool_min'],
                    max=db_config['pool_max'],
                    increment=db_config['pool_increment']
                )
                
                await self._test_connection()
                print("Oracle 공식 방법으로 연결 성공!")
                
                self._is_connected = True
                print("Oracle 데이터베이스 연결 성공!")
                print(f"- 연결 방식: Oracle 공식 방법")
                print(f"- Wallet 경로: {abs_wallet_path}")
                print(f"- 사용자: {db_config['db_user']}")
                return True
                
            except Exception as e:
                print(f"Oracle 공식 방법 연결 실패: {e}")
                return False
            
        except Exception as e:
            print(f"데이터베이스 초기화 중 예외: {str(e)}")
            return False
    
    async def _test_connection(self):
        """연결 테스트"""
        test_connection = self.connection_pool.acquire()
        cursor = test_connection.cursor()
        
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()
        
        cursor.execute("SELECT USER FROM DUAL")
        user_result = cursor.fetchone()
        
        cursor.close()
        test_connection.close()
        
        if result[0] == 1:
            print(f"연결 풀 테스트 성공 (사용자: {user_result[0]})")
        else:
            raise Exception("연결 테스트 결과가 예상과 다름")
    
    async def cleanup(self):
        """연결 풀 정리"""
        if self.connection_pool:
            try:
                self.connection_pool.close()
                self._is_connected = False
                print("Oracle 연결 풀이 정리되었습니다.")
            except Exception as e:
                print(f"연결 풀 정리 중 오류: {str(e)}")
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected and self.connection_pool is not None
    
    @asynccontextmanager
    async def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        if not self.is_connected():
            raise RuntimeError("데이터베이스 연결 풀이 초기화되지 않았습니다.")
        
        connection = None
        try:
            connection = self.connection_pool.acquire()
            yield connection
        except Exception as e:
            print(f"데이터베이스 연결 오류: {str(e)}")
            raise
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as close_error:
                    print(f"연결 해제 중 오류: {close_error}")
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, fetch_one: bool = True):
        """쿼리 실행"""
        try:
            async with self.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(query, params or {})
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                cursor.close()
                return result
        except Exception as e:
            print(f"쿼리 실행 중 오류: {str(e)}")
            return None
    
    async def execute_query_all(self, query: str, params: Optional[Dict[str, Any]] = None):
        """다중 결과 쿼리 실행"""
        return await self.execute_query(query, params, fetch_one=False)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """연결 정보 반환"""
        return {
            "is_connected": self.is_connected(),
            "connection_type": "Oracle Official Method",
            "wallet_path": self.settings.WALLET_PATH,
            "service_name": self.settings.ORACLE_SERVICE_NAME,
            "db_user": self.settings.DB_USER,
            "pool_status": {
                "opened": self.connection_pool.opened if self.connection_pool else 0,
                "busy": self.connection_pool.busy if self.connection_pool else 0,
                "max": self.connection_pool.max if self.connection_pool else 0
            } if self.connection_pool else None
        }