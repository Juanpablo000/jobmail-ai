from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.services.gmail_service import GmailService

router = APIRouter(tags=["auth"])
gmail_service = GmailService()


@router.get("/auth/login")
async def login():
    """
    Inicia el flujo OAuth2 con Gmail.
    Redirige al usuario a la página de autorización de Google.
    Requiere credentials.json en backend/.
    """
    try:
        auth_url = gmail_service.get_authorization_url()
        return RedirectResponse(url=auth_url)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "credentials.json no encontrado",
                "instrucciones": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando URL de autenticación: {e}")


@router.get("/auth/callback")
async def oauth_callback(code: str = None, error: str = None):
    """
    Callback de Google OAuth2.
    Recibe el código de autorización, lo intercambia por tokens y redirige al frontend.
    """
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Error de autenticación de Google: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="No se recibió código de autorización",
        )

    try:
        await gmail_service.exchange_code(code)
        return RedirectResponse(url="http://localhost:5173/?auth=success")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al intercambiar código por token: {e}",
        )


@router.get("/auth/status")
async def auth_status():
    """Verifica si el usuario está autenticado con Gmail."""
    return {
        "authenticated": GmailService.is_authenticated(),
        "message": "Autenticado con Gmail" if GmailService.is_authenticated()
                   else "No autenticado. Visita /auth/login",
    }
