from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import uvicorn
import sys
import os
import atexit

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 직접 import
from config.settings import Settings
from services.ai_classifier import AIClassifierService
from services.legacy_service import LegacyService
from services.price_service import PriceService

# 애플리케이션 설정
settings = Settings()

app = FastAPI(
    title="Image Classification API", 
    version="1.0.0",
    description="AI 이미지 분류 및 가격 정보 제공 서비스 (Legacy API 연동)",
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
legacy_service: LegacyService = None
price_service: PriceService = None
scheduler: AsyncIOScheduler = None

# 재시작 시도 카운터
restart_attempts = {
    "ai_service": 0,
    "legacy_service": 0
}
MAX_RESTART_ATTEMPTS = 3


async def initialize_services():
    """모든 서비스 초기화"""
    global ai_service, legacy_service, price_service
    
    print("🚀 서비스 초기화를 시작합니다...")
    
    # AI 분류 서비스 초기화
    print("📡 AI 분류 서비스 로딩 중...")
    if ai_service is None:
        ai_service = AIClassifierService(settings.MODEL_PATH)
    
    model_loaded = await ai_service.load_model()
    
    if model_loaded:
        print("✅ AI 모델이 성공적으로 로드되었습니다.")
        restart_attempts["ai_service"] = 0  # 성공 시 카운터 리셋
    else:
        print("❌ AI 모델 로드에 실패했습니다.")
        restart_attempts["ai_service"] += 1
    
    # Legacy 서비스 초기화
    print("🔗 Legacy 서비스 연결 중...")
    if legacy_service is None:
        legacy_service = LegacyService(settings)
    
    legacy_connected = await legacy_service.initialize()
    
    if legacy_connected:
        print("✅ Legacy 서비스 연결이 성공했습니다.")
        restart_attempts["legacy_service"] = 0  # 성공 시 카운터 리셋
        
        # 가격 서비스 초기화 (Legacy 연결 성공시에만)
        if price_service is None:
            price_service = PriceService(legacy_service)
        print("💰 가격 서비스가 초기화되었습니다.")
        
        # Legacy API 상태 확인
        health_status = await price_service.health_check()
        if health_status.get("legacy_api_available"):
            print("✅ Legacy API가 정상 작동 중입니다.")
        else:
            print(f"⚠️ Legacy API 연결에 문제가 있습니다: {health_status.get('error', 'Unknown error')}")
    else:
        print("⚠️ Legacy 서비스 연결에 실패했습니다. 가격 정보 기능이 비활성화됩니다.")
        restart_attempts["legacy_service"] += 1
    
    print("🎉 모든 서비스 초기화가 완료되었습니다!")
    return model_loaded and legacy_connected


async def health_check_and_restart():
    """헬스체크 및 필요시 서비스 재시작"""
    global ai_service, legacy_service, price_service
    
    print(f"\n🏥 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 정기 헬스체크 시작...")
    
    needs_restart = False
    
    # AI 서비스 체크
    if ai_service is None or not ai_service.is_loaded():
        print("⚠️ AI 서비스가 비정상 상태입니다.")
        if restart_attempts["ai_service"] < MAX_RESTART_ATTEMPTS:
            needs_restart = True
        else:
            print(f"❌ AI 서비스 재시작 최대 시도 횟수({MAX_RESTART_ATTEMPTS})를 초과했습니다.")
    else:
        print("✅ AI 서비스 정상")
    
    # Legacy 서비스 체크
    if legacy_service is None:
        print("⚠️ Legacy 서비스가 비정상 상태입니다.")
        if restart_attempts["legacy_service"] < MAX_RESTART_ATTEMPTS:
            needs_restart = True
        else:
            print(f"❌ Legacy 서비스 재시작 최대 시도 횟수({MAX_RESTART_ATTEMPTS})를 초과했습니다.")
    else:
        # Legacy API 상태 확인
        if price_service:
            health_status = await price_service.health_check()
            if health_status.get("legacy_api_available"):
                print("✅ Legacy 서비스 정상")
            else:
                print(f"⚠️ Legacy API 연결 불가: {health_status.get('error')}")
                if restart_attempts["legacy_service"] < MAX_RESTART_ATTEMPTS:
                    needs_restart = True
    
    # 재시작 필요 시 실행
    if needs_restart:
        print("🔄 서비스 재시작을 시도합니다...")
        try:
            # 기존 리소스 정리
            if price_service:
                await price_service.cleanup()
            if legacy_service:
                await legacy_service.cleanup()
            
            # 서비스 재초기화
            success = await initialize_services()
            
            if success:
                print("✅ 서비스 재시작이 성공했습니다.")
            else:
                print("⚠️ 서비스 재시작이 부분적으로 실패했습니다.")
                
        except Exception as e:
            print(f"❌ 서비스 재시작 중 오류 발생: {str(e)}")
    else:
        print("✅ 모든 서비스가 정상 상태입니다.")
    
    print("🏥 헬스체크 완료\n")


@app.on_event("startup")
async def startup_event():
    """서버 시작시 모든 서비스 초기화 및 스케줄러 설정"""
    global scheduler
    
    # 서비스 초기화
    success = await initialize_services()
    
    if not success:
        print("⚠️ 초기 서비스 시작에 실패했습니다. 스케줄러가 자동으로 재시도합니다.")
    
    # 스케줄러 설정
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
    health_check_and_restart,
    trigger=CronTrigger(minute=0),
    id="hourly_health_check",
    name="Hourly Health Check",
    replace_existing=True
)
    
    scheduler.start()
    
    # 다음 실행 시간 출력
    jobs = scheduler.get_jobs()
    for job in jobs:
        print(f"   📅 {job.name}: 다음 실행 - {job.next_run_time}")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료시 리소스 정리"""
    global scheduler
    
    print("🔄 서비스 정리 중...")
    
    # 스케줄러 종료
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("⏰ 스케줄러가 종료되었습니다.")
    
    if price_service:
        await price_service.cleanup()
    
    if legacy_service:
        await legacy_service.cleanup()
    
    print("✅ 서비스 정리가 완료되었습니다.")


# 프로세스 종료 시에도 정리 작업 수행
def cleanup_on_exit():
    """프로세스 종료 시 정리 작업"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.run_until_complete(shutdown_event())
    except:
        pass

atexit.register(cleanup_on_exit)


# === API 엔드포인트들 ===

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Image Classification API (Legacy Integration)", 
        "status": "running",
        "version": "1.0.0",
        "scheduler": "active" if scheduler and scheduler.running else "inactive"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    # Legacy API 상태도 함께 확인
    legacy_health = None
    if price_service:
        legacy_health = await price_service.health_check()
    
    # 스케줄러 정보
    scheduler_info = None
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        scheduler_info = {
            "running": True,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        }
    
    return {
        "status": "healthy",
        "services": {
            "ai_model": ai_service is not None and ai_service.is_loaded(),
            "legacy_service": legacy_service is not None,
            "price_service": price_service is not None,
            "legacy_api": legacy_health.get("legacy_api_available", False) if legacy_health else False,
            "scheduler": scheduler is not None and scheduler.running
        },
        "restart_attempts": restart_attempts,
        "legacy_api_info": legacy_health if legacy_health else None,
        "scheduler_info": scheduler_info
    }


@app.post("/predict")
async def predict_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    이미지 파일을 받아서 카테고리를 예측하고 가격 정보 제공 (Legacy API 연동)
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
        
        # 각 예측에 대한 가격 정보 조회 (Legacy API 호출)
        for prediction in predictions:
            if price_service and price_service.is_available():
                print(f"🔍 카테고리 '{prediction['category']}' 가격 정보 조회 중...")
                price_info = await price_service.get_category_price_range(
                    prediction["category"]
                )
                prediction["price_info"] = price_info
                
                if price_info:
                    print(f"✅ 가격 정보 조회 완료")
                else:
                    print(f"❌ 가격 정보 조회 실패")
            else:
                prediction["price_info"] = None
                print(f"⚠️ 가격 서비스가 비활성화되어 있습니다.")
        
        # 응답 구성 (기존 구조 유지)
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
        print(f"❌ 예측 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"예측 중 오류 발생: {str(e)}"
        )


@app.get("/service-status")
async def get_service_status():
    """서비스 상태 상세 정보 엔드포인트"""
    status = {
        "ai_service": {
            "available": ai_service is not None,
            "model_loaded": ai_service.is_loaded() if ai_service else False,
            "model_path": settings.MODEL_PATH,
            "restart_attempts": restart_attempts["ai_service"]
        },
        "legacy_service": {
            "available": legacy_service is not None,
            "legacy_path": settings.LEGACY_PATH,
            "restart_attempts": restart_attempts["legacy_service"]
        },
        "price_service": None,
        "scheduler": {
            "running": scheduler is not None and scheduler.running,
            "jobs": []
        }
    }
    
    # 가격 서비스 상태 정보
    if price_service:
        status["price_service"] = price_service.get_service_status()
        # Legacy API 헬스체크
        health_check_result = await price_service.health_check()
        status["price_service"]["health_check"] = health_check_result
    
    # 스케줄러 작업 정보
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        status["scheduler"]["jobs"] = [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    
    return status


@app.post("/restart")
async def manual_restart():
    """수동 서비스 재시작 엔드포인트"""
    try:
        print("🔄 수동 서비스 재시작 요청...")
        await health_check_and_restart()
        return {
            "success": True,
            "message": "서비스 재시작이 완료되었습니다.",
            "restart_attempts": restart_attempts
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"서비스 재시작 실패: {str(e)}"
        )


# === 헬퍼 함수들 ===

def _build_price_recommendation(category: str, price_info: dict) -> dict:
    """가격 추천 정보 구성 (기존 구조 유지)"""
    return {
        "category": category,
        "average_price": price_info.get("average_price") if price_info else None,
        "price_range": {
            "min": price_info.get("min_price") if price_info else None,
            "max": price_info.get("max_price") if price_info else None,
            "median": price_info.get("median_price") if price_info else None
        } if price_info else None,
        "product_count": price_info.get("product_count", 0) if price_info else 0,
        "db_connected": legacy_service is not None and legacy_service.is_connected()
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
    print(f"   Legacy API 연동 모드")
    print(f"   자동 재시작: 매일 자정")
    
    uvicorn.run(
        "main:app",
        host=server_config['host'],
        port=server_config['port'],
        reload=True,
        log_level=server_config['log_level']
    )