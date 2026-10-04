from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .phone_login import (
    CodeSent,
    CompleteLogin,
    LoginGranted,
    NonprofitPhoneLogin,
    StartLogin,
)

app = FastAPI(title="Nonprofit phone login")


def workflow() -> NonprofitPhoneLogin:
    return NonprofitPhoneLogin(InfraiClient())


@app.post("/login/code", response_model=CodeSent)
def send_code(command: StartLogin) -> CodeSent:
    client_workflow = workflow()
    try:
        return client_workflow.start(command)
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=error.details) from error
    finally:
        client_workflow.close()


@app.post("/login/complete", response_model=LoginGranted)
def complete_login(command: CompleteLogin) -> LoginGranted:
    client_workflow = workflow()
    try:
        return client_workflow.complete(command)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=error.details) from error
    finally:
        client_workflow.close()
