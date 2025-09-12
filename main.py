"""
Image Classification API
이미지 분류 및 가격 정보 제공 FastAPI 애플리케이션
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 직접 import
from config.settings import Settings
from services.ai_classifier import AIClassifierService
from services.database_service import DatabaseService
from services.price_service import PriceService

# 애플리케이션 설정
settings = Settings()

app = FastAPI(
    title="Image Classification API", 
    version="1.0.0",
    description="AI 이미지 분류 및 가격 정보 제공 서비스",
    root_path="/ai"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 서비스 인스턴스
ai_service: AIClassifierService = None
db_service: DatabaseService = None
price_service: PriceService = None


@app.on_event("startup")
async def startup_event():
    """서버 시작시 모든 서비스 초기화"""
    global ai_service, db_service, price_service
    
    print("🚀 서비스 초기화를 시작합니다...")
    
    # AI 분류 서비스 초기화
    print("📡 AI 분류 서비스 로딩 중...")
    ai_service = AIClassifierService(settings.MODEL_PATH)
    model_loaded = await ai_service.load_model()
    
    if model_loaded:
        print("✅ AI 모델이 성공적으로 로드되었습니다.")
    else:
        print("❌ AI 모델 로드에 실패했습니다.")
    
    # 데이터베이스 서비스 초기화
    print("💾 데이터베이스 연결 중...")
    db_service = DatabaseService(settings)
    db_connected = await db_service.initialize()
    
    if db_connected:
        print("✅ 데이터베이스 연결이 성공했습니다.")
        # 가격 서비스 초기화 (DB 연결 성공시에만)
        price_service = PriceService(db_service)
        print("💰 가격 서비스가 초기화되었습니다.")
    else:
        print("⚠️ 데이터베이스 연결에 실패했습니다. 가격 정보 기능이 비활성화됩니다.")
        price_service = None
    
    print("🎉 모든 서비스 초기화가 완료되었습니다!")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료시 리소스 정리"""
    print("🔄 서비스 정리 중...")
    
    if db_service:
        await db_service.cleanup()
    
    print("✅ 서비스 정리가 완료되었습니다.")


# === API 엔드포인트들 ===

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Image Classification API", 
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "services": {
            "ai_model": ai_service is not None and ai_service.is_loaded(),
            "database": db_service is not None and db_service.is_connected(),
            "price_service": price_service is not None and price_service.is_available()
        }
    }


@app.post("/predict")
async def predict_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    이미지 파일을 받아서 카테고리를 예측하고 가격 정보 제공
    """
    
    # 서비스 가용성 체크
    if not ai_service or not ai_service.is_loaded():
        raise HTTPException(
            status_code=503, 
            detail="AI 분류 서비스가 사용 불가능합니다."
        )
    
    # 파일 타입 검증
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, 
            detail="이미지 파일만 업로드 가능합니다."
        )
    
    try:
        # 이미지 분류 수행
        contents = await file.read()
        predictions = await ai_service.predict(contents)
        
        # 각 예측에 대한 가격 정보 조회
        for prediction in predictions:
            if price_service and price_service.is_available():
                price_info = await price_service.get_category_price_range(
                    prediction["category"]
                )
                prediction["price_info"] = price_info
            else:
                prediction["price_info"] = None
        
        # 응답 구성
        top_prediction = predictions[0]
        top_price_info = top_prediction.get("price_info")
        
        response = {
            "success": True,
            "filename": file.filename,
            "predictions": predictions,
            "top_category": top_prediction["category"],
            "top_confidence": top_prediction["confidence"],
            "price_recommendation": _build_price_recommendation(
                top_prediction["category"], 
                top_price_info
            )
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"예측 중 오류 발생: {str(e)}"
        )


@app.get("/price/{category_name}")
async def get_category_price(category_name: str):
    """특정 카테고리의 가격 정보 조회"""
    if not price_service or not price_service.is_available():
        raise HTTPException(
            status_code=503, 
            detail="가격 서비스가 사용 불가능합니다."
        )
    
    price_info = await price_service.get_category_price_range(category_name)
    if price_info is None:
        raise HTTPException(
            status_code=404, 
            detail=f"카테고리 '{category_name}'의 가격 정보를 찾을 수 없습니다."
        )
    
    return {
        "category": category_name,
        "db_category": price_service.get_db_category_name(category_name),
        "price_info": price_info
    }


@app.get("/categories")
async def get_categories():
    """사용 가능한 카테고리 목록 반환"""
    if not ai_service:
        raise HTTPException(
            status_code=503, 
            detail="AI 서비스가 초기화되지 않았습니다."
        )
    
    categories = ai_service.get_categories()
    return {
        "categories": [
            {"id": i, "name": name} 
            for i, name in enumerate(categories)
        ],
        "total_categories": len(categories)
    }


@app.get("/summary/{category_name}")
async def get_category_summary(category_name: str):
    """카테고리별 상품 요약 정보 조회"""
    if not price_service or not price_service.is_available():
        raise HTTPException(
            status_code=503, 
            detail="가격 서비스가 사용 불가능합니다."
        )
    
    summary = await price_service.get_category_products_summary(category_name)
    if summary is None:
        raise HTTPException(
            status_code=404, 
            detail=f"카테고리 '{category_name}'의 요약 정보를 찾을 수 없습니다."
        )
    
    return {
        "category": category_name,
        "summary": summary
    }


# === 헬퍼 함수들 ===

def _build_price_recommendation(category: str, price_info: dict) -> dict:
    """가격 추천 정보 구성"""
    return {
        "category": category,
        "average_price": price_info.get("average_price") if price_info else None,
        "price_range": {
            "min": price_info.get("min_price") if price_info else None,
            "max": price_info.get("max_price") if price_info else None,
            "median": price_info.get("median_price") if price_info else None
        } if price_info else None,
        "product_count": price_info.get("product_count", 0) if price_info else 0,
        "db_connected": db_service is not None and db_service.is_connected()
    }


if __name__ == "__main__":
    # 설정 검증
    if not settings.validate_all():
        print("❌ 설정이 올바르지 않습니다. 서버를 시작할 수 없습니다.")
        exit(1)
    
    # 서버 설정 가져오기
    server_config = settings.get_server_config()
    
    print(f"🚀 서버 시작: {server_config['host']}:{server_config['port']}")
    print(f"   Workers: {server_config['workers']}")
    print(f"   Log Level: {server_config['log_level']}")
    
    uvicorn.run(
        "main:app",
        host=server_config['host'],
        port=server_config['port'],
        reload=True,
        log_level=server_config['log_level']
    )