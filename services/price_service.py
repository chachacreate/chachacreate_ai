"""
가격 정보 조회 및 분석 서비스
AI 카테고리 기반 상품 가격 통계 제공
"""

from typing import Optional, Dict, Any, List
from .database_service import DatabaseService

class PriceService:
    """가격 정보 조회 및 분석 서비스"""
    
    # AI 모델 카테고리와 DB 카테고리 매핑 테이블
    AI_TO_DB_CATEGORY_MAP = {
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
    
    def __init__(self, database_service: DatabaseService):
        """
        초기화
        
        Args:
            database_service: 데이터베이스 서비스 인스턴스
        """
        self.db_service = database_service
    
    def is_available(self) -> bool:
        """
        가격 서비스 사용 가능 여부 확인
        
        Returns:
            서비스 사용 가능 여부
        """
        return self.db_service and self.db_service.is_connected()
    
    def get_db_category_name(self, ai_category: str) -> Optional[str]:
        """
        AI 카테고리를 DB 카테고리명으로 변환
        
        Args:
            ai_category: AI 모델의 카테고리명
            
        Returns:
            DB의 카테고리명 또는 None
        """
        return self.AI_TO_DB_CATEGORY_MAP.get(ai_category)
    
    def get_all_category_mappings(self) -> Dict[str, str]:
        """
        모든 카테고리 매핑 정보 반환
        
        Returns:
            AI 카테고리 -> DB 카테고리 매핑 딕셔너리
        """
        return self.AI_TO_DB_CATEGORY_MAP.copy()
    
    async def get_category_average_price(self, category_name: str) -> Optional[float]:
        """
        카테고리별 평균 가격 조회 (단순 평균)
        
        Args:
            category_name: AI 모델의 카테고리명
            
        Returns:
            평균 가격 또는 None
        """
        if not self.is_available():
            print("❌ 데이터베이스 서비스가 사용 불가능합니다.")
            return None
        
        db_category_name = self.get_db_category_name(category_name)
        if not db_category_name:
            print(f"❌ 카테고리 매핑을 찾을 수 없습니다: {category_name}")
            return None
        
        query = """
        SELECT 
            AVG(p.price) as avg_price, 
            COUNT(*) as product_count
        FROM product p 
        JOIN d_category dc ON p.d_category_id = dc.d_category_id 
        WHERE dc.d_category_name = :category_name 
        AND p.delete_check = 0
        AND p.price > 0
        """
        
        try:
            result = await self.db_service.execute_query(
                query, 
                {"category_name": db_category_name}
            )
            
            if result and result[0] is not None:
                avg_price = float(result[0])
                product_count = int(result[1])
                
                print(f"💰 카테고리 '{db_category_name}': "
                      f"평균가격 {avg_price:,.0f}원, 상품수 {product_count}개")
                return avg_price
            else:
                print(f"📭 카테고리 '{db_category_name}'에 대한 상품이 없습니다.")
                return None
                
        except Exception as e:
            print(f"❌ 평균 가격 조회 중 오류: {str(e)}")
            return None
    
    async def get_category_price_range(self, category_name: str) -> Optional[Dict[str, Any]]:
        """
        카테고리별 상세 가격 통계 조회 (최소, 최대, 평균, 중앙값)
        
        Args:
            category_name: AI 모델의 카테고리명
            
        Returns:
            가격 통계 정보 딕셔너리 또는 None
        """
        if not self.is_available():
            return None
        
        db_category_name = self.get_db_category_name(category_name)
        if not db_category_name:
            print(f"❌ 카테고리 매핑을 찾을 수 없습니다: {category_name}")
            return None
        
        query = """
        SELECT 
            AVG(p.price) as avg_price,
            MIN(p.price) as min_price,
            MAX(p.price) as max_price,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.price) as median_price,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY p.price) as q1_price,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY p.price) as q3_price,
            COUNT(*) as product_count,
            STDDEV(p.price) as price_stddev
        FROM product p 
        JOIN d_category dc ON p.d_category_id = dc.d_category_id 
        WHERE dc.d_category_name = :category_name 
        AND p.delete_check = 0
        AND p.price > 0
        """
        
        try:
            result = await self.db_service.execute_query(
                query, 
                {"category_name": db_category_name}
            )
            
            if result and result[0] is not None:
                price_stats = {
                    "average_price": float(result[0]),
                    "min_price": float(result[1]),
                    "max_price": float(result[2]),
                    "median_price": float(result[3]),
                    "q1_price": float(result[4]) if result[4] else None,
                    "q3_price": float(result[5]) if result[5] else None,
                    "product_count": int(result[6]),
                    "price_stddev": float(result[7]) if result[7] else 0.0,
                    "db_category": db_category_name,
                    "ai_category": category_name
                }
                
                # 가격 범위 계산
                price_stats["price_range"] = price_stats["max_price"] - price_stats["min_price"]
                
                print(f"📊 카테고리 '{db_category_name}' 가격 통계:")
                print(f"   평균: {price_stats['average_price']:,.0f}원")
                print(f"   범위: {price_stats['min_price']:,.0f}원 ~ {price_stats['max_price']:,.0f}원")
                print(f"   중앙값: {price_stats['median_price']:,.0f}원")
                print(f"   상품수: {price_stats['product_count']}개")
                
                return price_stats
            else:
                print(f"📭 카테고리 '{db_category_name}'에 대한 가격 정보가 없습니다.")
                return None
                
        except Exception as e:
            print(f"❌ 가격 범위 조회 중 오류: {str(e)}")
            return None
    
    async def get_category_products_summary(self, category_name: str) -> Optional[Dict[str, Any]]:
        """
        카테고리별 상품 요약 정보 조회
        
        Args:
            category_name: AI 모델의 카테고리명
            
        Returns:
            상품 요약 정보 딕셔너리 또는 None
        """
        if not self.is_available():
            return None
        
        db_category_name = self.get_db_category_name(category_name)
        if not db_category_name:
            return None
        
        query = """
        SELECT 
            COUNT(*) as total_products,
            COUNT(CASE WHEN p.stock > 0 THEN 1 END) as in_stock_products,
            COUNT(CASE WHEN p.stock = 0 THEN 1 END) as out_of_stock_products,
            SUM(p.sale_cnt) as total_sales,
            AVG(p.view_cnt) as avg_views,
            MAX(p.view_cnt) as max_views,
            COUNT(CASE WHEN p.flagship_check = 1 THEN 1 END) as flagship_products,
            AVG(p.price) as avg_price,
            MAX(p.product_date) as latest_product_date
        FROM product p 
        JOIN d_category dc ON p.d_category_id = dc.d_category_id 
        WHERE dc.d_category_name = :category_name 
        AND p.delete_check = 0
        """
        
        try:
            result = await self.db_service.execute_query(
                query, 
                {"category_name": db_category_name}
            )
            
            if result and result[0] is not None:
                summary = {
                    "total_products": int(result[0]) if result[0] else 0,
                    "in_stock_products": int(result[1]) if result[1] else 0,
                    "out_of_stock_products": int(result[2]) if result[2] else 0,
                    "total_sales": int(result[3]) if result[3] else 0,
                    "average_views": float(result[4]) if result[4] else 0.0,
                    "max_views": int(result[5]) if result[5] else 0,
                    "flagship_products": int(result[6]) if result[6] else 0,
                    "average_price": float(result[7]) if result[7] else 0.0,
                    "latest_product_date": result[8],
                    "db_category": db_category_name,
                    "ai_category": category_name
                }
                
                # 재고 비율 계산
                if summary["total_products"] > 0:
                    summary["stock_ratio"] = summary["in_stock_products"] / summary["total_products"]
                    summary["flagship_ratio"] = summary["flagship_products"] / summary["total_products"]
                else:
                    summary["stock_ratio"] = 0.0
                    summary["flagship_ratio"] = 0.0
                
                print(f"📈 카테고리 '{db_category_name}' 상품 요약:")
                print(f"   총 상품: {summary['total_products']}개")
                print(f"   재고 있음: {summary['in_stock_products']}개 ({summary['stock_ratio']:.1%})")
                print(f"   총 판매: {summary['total_sales']}건")
                print(f"   평균 조회수: {summary['average_views']:.1f}")
                
                return summary
            else:
                return None
                
        except Exception as e:
            print(f"❌ 상품 요약 조회 중 오류: {str(e)}")
            return None
    
    async def get_trending_categories(self, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """
        인기 카테고리 조회 (판매량 기준)
        
        Args:
            limit: 반환할 카테고리 개수
            
        Returns:
            인기 카테고리 리스트 또는 None
        """
        if not self.is_available():
            return None
        
        query = """
        SELECT 
            dc.d_category_name,
            COUNT(p.product_id) as product_count,
            SUM(p.sale_cnt) as total_sales,
            AVG(p.price) as avg_price,
            SUM(p.view_cnt) as total_views
        FROM product p 
        JOIN d_category dc ON p.d_category_id = dc.d_category_id 
        WHERE p.delete_check = 0
        AND p.price > 0
        GROUP BY dc.d_category_name
        ORDER BY SUM(p.sale_cnt) DESC, SUM(p.view_cnt) DESC
        """
        
        try:
            results = await self.db_service.execute_query_all(query)
            
            if results:
                trending = []
                for i, row in enumerate(results[:limit]):
                    # DB 카테고리에서 AI 카테고리 찾기
                    ai_category = None
                    for ai_cat, db_cat in self.AI_TO_DB_CATEGORY_MAP.items():
                        if db_cat == row[0]:
                            ai_category = ai_cat
                            break
                    
                    trending.append({
                        "rank": i + 1,
                        "db_category": row[0],
                        "ai_category": ai_category,
                        "product_count": int(row[1]),
                        "total_sales": int(row[2]) if row[2] else 0,
                        "average_price": float(row[3]) if row[3] else 0.0,
                        "total_views": int(row[4]) if row[4] else 0
                    })
                
                print(f"🔥 인기 카테고리 TOP {len(trending)}:")
                for item in trending:
                    print(f"   {item['rank']}. {item['db_category']} "
                          f"(판매: {item['total_sales']}건, 상품: {item['product_count']}개)")
                
                return trending
            return None
            
        except Exception as e:
            print(f"❌ 인기 카테고리 조회 중 오류: {str(e)}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        가격 서비스 상태 정보 반환
        
        Returns:
            서비스 상태 정보 딕셔너리
        """
        return {
            "is_available": self.is_available(),
            "database_connected": self.db_service.is_connected() if self.db_service else False,
            "supported_categories": len(self.AI_TO_DB_CATEGORY_MAP),
            "category_mappings": self.AI_TO_DB_CATEGORY_MAP,
            "database_info": self.db_service.get_connection_info() if self.db_service else None
        }