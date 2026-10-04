import os
import uuid

from nonprofit_login.infrai_client import InfraiClient
from nonprofit_login.phone_login import NonprofitPhoneLogin, StartLogin


phone = os.environ["DEMO_PHONE"]
client = InfraiClient()
try:
    result = NonprofitPhoneLogin(client).start(
        StartLogin(phone=phone, locale="en", request_id=str(uuid.uuid4()))
    )
    print(result.model_dump_json())
finally:
    client.close()

