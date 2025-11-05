import uuid
import pkce
import random
import requests

from typing import NamedTuple

class PayPayUtils:
    SENTRY_PUBLIC = "e5f3c063d55d3058bc5bfb0f311152e4"

    @staticmethod
    def generate_sentry():
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[16:]

        class SentryTraceSpan(NamedTuple):
            trace_id: str
            span_id: str

            sentry_trace: str
            sentry_trace_0: str
            sentry_trace_1: str

        return SentryTraceSpan(
            trace_id,
            span_id,
            f"{trace_id}-{span_id}",
            f"{trace_id}-{span_id}-0",
            f"{trace_id}-{span_id}-1"
        )
    
    @staticmethod
    def generate_vector(r1, r2, r3, precision=8):
        v1 = f"{random.uniform(*r1):.{precision}f}"
        v2 = f"{random.uniform(*r2):.{precision}f}"
        v3 = f"{random.uniform(*r3):.{precision}f}"
        return f"{v1}_{v2}_{v3}"
    
    @staticmethod
    def generate_device_state():
        device_orientation = PayPayUtils.generate_vector(
            (2.2, 2.6),
            (-0.2, -0.05),
            (-0.05, 0.1)
        )
        device_orientation_2 = PayPayUtils.generate_vector(
            (2.0, 2.6),
            (-0.2, -0.05),
            (-0.05, 0.2)
        )

        device_rotation = PayPayUtils.generate_vector(
            (-0.8, -0.6),
            (0.65, 0.8),
            (-0.12, -0.04)
        )
        device_rotation_2 = PayPayUtils.generate_vector(
            (-0.85, -0.4),
            (0.53, 0.9),
            (-0.15, -0.03)
        )

        device_acceleration = PayPayUtils.generate_vector(
            (-0.35, 0.0),
            (-0.01, 0.3),
            (-0.1, 0.1)
        )
        device_acceleration_2 = PayPayUtils.generate_vector(
            (0.01, 0.04),
            (-0.04, 0.09),
            (-0.03, 0.1)
        )

        class DeviceHeaders(NamedTuple):
            device_orientation: str
            device_orientation_2: str
            device_rotation: str
            device_rotation_2: str
            device_acceleration: str
            device_acceleration_2: str

        return DeviceHeaders(
            device_orientation,
            device_orientation_2,
            device_rotation,
            device_rotation_2,
            device_acceleration,
            device_acceleration_2
        )
    
    @staticmethod
    def set_device_state_to_headers(headers):
        device_state = PayPayUtils.generate_device_state()

        headers["Device-Orientation"] = device_state.device_orientation
        headers["Device-Orientation-2"] = device_state.device_orientation_2
        headers["Device-Rotation"] = device_state.device_rotation
        headers["Device-Rotation-2"] = device_state.device_rotation_2
        headers["Device-Acceleration"] = device_state.device_acceleration
        headers["Device-Acceleration-2"] = device_state.device_acceleration_2

        return headers
    
    @staticmethod
    def set_baggage_to_headers(headers, public_key, sample_rate, sampled, transaction, sentry_trace_style):
        baggage = "sentey-environment=Production," + f"sentry-public_key={public_key},sentry-release=consumer-android%404.78.1%2B47801"
        if sample_rate:
            baggage = baggage + f",sentry-sample_rate={sample_rate}"

        if sampled != None:
            if sampled:
                baggage = baggage + ",sentry-sampled=true"
            else:
                baggage = baggage + ",sentry-sampled=false"

        sentry_ids = PayPayUtils.generate_sentry()
        baggage = baggage + f",sentry-trace_id={sentry_ids.trace_id}"

        if transaction:
            baggage = baggage + f",sentry-transaction={transaction}"

        if sentry_trace_style == 0:
            headers["sentry-trace"] = sentry_ids.sentry_trace_0
        elif sentry_trace_style == 1:
            headers["sentry-trace"] = sentry_ids.sentry_trace_1
        else:
            headers["sentry-trace"] = sentry_ids.sentry_trace
        
        headers["baggage"] = baggage
        return headers
    
class PayPay:
    def __init__(self, access_token=None, device_uuid=str(uuid.uuid4()), client_uuid=str(uuid.uuid4())):
        self.access_token = access_token
        self.device_uuid = device_uuid
        self.client_uuid = client_uuid

        self.session = requests.Session()

        device_state = PayPayUtils.generate_device_state()

        self.paypay_version = "4.78.1"

        self.params = {
            "payPayLang": "ja"
        }

        self.headers = {
            "Accept": "*/*",
            "Accept-Charset": "UTF-8",
            "Accept-Encoding": "gzip",
            "Client-Mode": "NORMAL",
            "Client-OS-Release-Version": "10",
            "Client-OS-Type": "ANDROID",
            "Client-OS-Version": "29.0.0",
            "Client-Type": "PAYPAYAPP",
            "Client-UUID": self.client_uuid,
            "Client-Version": self.paypay_version,
            "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Device-Acceleration": device_state.device_acceleration,
            "Device-Acceleration-2": device_state.device_acceleration_2,
            "Device-Brand-Name": "KDDI",
            "Device-Hardware-Name": "qcom",
            "Device-In-Call": "false",
            "Device-Lock-App-Setting": "false",
            "Device-Lock-Type": "NONE",
            "Device-Manufacturer-Name": "samsung",
            "Device-Name": "SCV38",
            "Device-Orientation": device_state.device_orientation,
            "Device-Orientation-2": device_state.device_orientation_2,
            "Device-Rotation": device_state.device_rotation,
            "Device-Rotation-2": device_state.device_rotation_2,
            "Device-UUID": self.device_uuid,
            "Host": "app4.paypay.ne.jp",
            "Is-Emulator": "false",
            "Network-Status": "WIFI",
            "System-Locale": "ja",
            "Timezone": "Asia/Tokyo",
            "User-Agent": f"PaypayApp/{self.paypay_version} Android10"
        }

        if access_token != None:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            self.headers["Content-Type"] = "application/json"

    def login_start(self, phone, password):
        if self.access_token != None:
            return False
        
        self.verifier, self.challenge = pkce.generate_pkce_pair(43)

        self.headers = PayPayUtils.set_baggage_to_headers(self.headers, PayPayUtils.SENTRY_PUBLIC, "0", False, "OAuth2Fragment", 0)

        _response = self.session.post(
            "https://app4.paypay.ne.jp/bff/v2/oauth2/par",
            params=self.params,
            headers=self.headers,
            data={
                "clientId": "pay2-mobile-app-client",
                "clientAppVersion": self.paypay_version,
                "clientOsVersion": "29.0.0",
                "clientOsType": "ANDROID",
                "redirectUri": "paypay://oauth2/callback",
                "responseType": "code",
                "state": pkce.generate_code_verifier(43),
                "codeChallenge": self.challenge,
                "codeChallengeMethod": "S256",
                "scope": "REGULAR",
                "tokenVersion": "v2",
                "prompt": "",
                "uiLocales": "ja"
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        self.session.get(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/authorize",
            params={
                "client_id": "pay2-mobile-app-client",
                "request_uri": response["payload"]["requestUri"]
            },
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Host": "www.paypay.ne.jp",
                "is-emulator": "false",
                "Pragma": "no-cache",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132"',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            }
        )

        self.session.get(
            "https://www.paypay.ne.jp/portal/oauth2/sign-in",
            params={
                "client_id": "pay2-mobile-app-client",
                "mode": "landing"
            },
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Host": "www.paypay.ne.jp",
                "is-emulator": "false",
                "Pragma": "no-cache",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132"',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            }
        )

        sentry_ids = PayPayUtils.generate_sentry()
        _response = self.session.get(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/par/check",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id},sentry-sample_rate=0.0005,sentry-transaction=SignIn,sentry-sampled=false",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-Type": "PAYPAYAPP",
                "Connection": "keep-alive",
                "Host": "www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/sign-in?client_id=pay2-mobile-app-client&mode=landing",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace_0,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        sentry_ids = PayPayUtils.generate_sentry()
        _response = self.session.post(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/sign-in/password",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id}",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-OS-Type": "ANDROID",
                "Client-OS-Version": "29.0.0",
                "Client-Type": "PAYPAYAPP",
                "Client-Version": self.paypay_version,
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "www.paypay.ne.jp",
                "Origin": "https://www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/sign-in?client_id=pay2-mobile-app-client&mode=landing",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            },
            json={
                "username": phone,
                "password": password,
                "signInAttemptCount": 1
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        try:
            uri = response["payload"]["redirectUrl"].replace("paypay://oauth2/callback?","").split("&")
            headers = self.headers
            del headers["Device-Lock-Type"]
            del headers["Device-Lock-App-Setting"]
            del headers["baggage"]
            del headers["sentry-trace"]

            _response = self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/oauth2/token",
                params=self.params,
                headers=headers,
                data={
                    "clientId": "pay2-mobile-app-client",
                    "redirectUri": "paypay://oauth2/callback",
                    "code": uri[0].replace("code=",""),
                    "codeVerifier": self.verifier
                }
            )
            try:
                response = _response.json()
                if response["header"]["resultCode"] != "S0000":
                    return False
            except:
                return False
            
            self.access_token= response["payload"]["accessToken"]
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            self.headers["Content-Type"] = "application/json"

            self.headers = PayPayUtils.set_device_state_to_headers(self.headers)

            return True
        except:
            pass

        _response = self.session.post(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id}",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-OS-Type": "ANDROID",
                "Client-OS-Version": "29.0.0",
                "Client-Type": "PAYPAYAPP",
                "Client-Version": self.paypay_version,
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "www.paypay.ne.jp",
                "Origin": "https://www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/sign-in?client_id=pay2-mobile-app-client&mode=landing",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            },
            json={}
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        _response = self.session.post(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id}",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-OS-Type": "ANDROID",
                "Client-OS-Version": "29.0.0",
                "Client-Type": "PAYPAYAPP",
                "Client-Version": self.paypay_version,
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "www.paypay.ne.jp",
                "Origin": "https://www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/verification-method?client_id=pay2-mobile-app-client&mode=navigation-2fa",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            },
            json={
                "params": {
                    "extension_id":"user-main-2fa-v1",
                    "data": {
                        "type": "SELECT_FLOW",
                        "payload": {
                            "flow": "OTL",
                            "sign_in_method": "MOBILE",
                            "base_url": "https://www.paypay.ne.jp/portal/oauth2/l"
                        }
                    }
                }
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        _response = self.session.post(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/side-channel/next-action-polling",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id}",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-OS-Type": "ANDROID",
                "Client-OS-Version": "29.0.0",
                "Client-Type": "PAYPAYAPP",
                "Client-Version": self.paypay_version,
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "www.paypay.ne.jp",
                "Origin": "https://www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": "https://www.paypay.ne.jp/portal/oauth2/otl-request?client_id=pay2-mobile-app-client&mode=navigation-2fa",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            },
            json={
                "waitUntil": "PT5S"
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                print(response)
                return False
        except:
            return False
        
        return True
    
    def login_confirm(self, accept_url):
        if "https://" in accept_url:
            accept_url = accept_url.replace("https://www.paypay.ne.jp/portal/oauth2/l?id=", "")

        sentry_ids = PayPayUtils.generate_sentry()
        _response = self.session.post(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/sign-in/2fa/otl/verify",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id},sentry-sample_rate=0.0005,sentry-transaction=OTL,sentry-sampled=false",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-OS-Type": "ANDROID",
                "Client-OS-Version": "29.0.0",
                "Client-Type": "PAYPAYAPP",
                "Client-Version": self.paypay_version,
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "www.paypay.ne.jp",
                "Origin": "https://www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": f"https://www.paypay.ne.jp/portal/oauth2/l?id={accept_url}&client_id=pay2-mobile-app-client",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace_0,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            },
            json={
                "code": accept_url
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        _response = self.session.post(
            "https://www.paypay.ne.jp/portal/api/v2/oauth2/extension/code-grant/update",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ja-JP,ja;q=0.9",
                "baggage": f"sentry-environment=Production,sentry-release=4.75.0,sentry-public_key=a5e3ae80a20e15b8de50274dd231ab83,sentry-trace_id={sentry_ids.trace_id},sentry-sample_rate=0.0005,sentry-transaction=OTL,sentry-sampled=false",
                "Cache-Control": "no-cache",
                "Client-Id": "pay2-mobile-app-client",
                "Client-OS-Type": "ANDROID",
                "Client-OS-Version": "29.0.0",
                "Client-Type": "PAYPAYAPP",
                "Client-Version": self.paypay_version,
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Host": "www.paypay.ne.jp",
                "Origin": "https://www.paypay.ne.jp",
                "Pragma": "no-cache",
                "Referer": f"https://www.paypay.ne.jp/portal/oauth2/l?id={accept_url}&client_id=pay2-mobile-app-client",
                "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Android WebView";v="132")',
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": '"Android"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "sentry-trace": sentry_ids.sentry_trace_0,
                "User-Agent": f"Mozilla/5.0 (Linux; Android 10; SCV38 Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6834.163 Mobile Safari/537.36 jp.pay2.app.android/{self.paypay_version}",
                "X-Requested-With": "jp.ne.paypay.android.app"
            },
            json={
                "params": {
                    "extension_id": "user-main-2fa-v1",
                    "data": {
                        "type": "COMPLETE_OTL",
                        "payload": None
                    }
                }
            }
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        try:
            uri = response["payload"]["redirect_uri"].replace("paypay://oauth2/callback?","").split("&")

            headers = self.headers
            del headers["Device-Lock-Type"]
            del headers["Device-Lock-App-Setting"]
            del headers["baggage"]
            del headers["sentry-trace"]

            _response = self.session.post(
                "https://app4.paypay.ne.jp/bff/v2/oauth2/token",
                params=self.params,
                headers=headers,
                data={
                    "clientId": "pay2-mobile-app-client",
                    "redirectUri": "paypay://oauth2/callback",
                    "code": uri[0].replace("code=",""),
                    "codeVerifier": self.verifier
                }
            )
            try:
                response = _response.json()
                if response["header"]["resultCode"] != "S0000":
                    return False
            except:
                return False
            
            self.access_token= response["payload"]["accessToken"]
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            self.headers["Content-Type"] = "application/json"

            self.headers = PayPayUtils.set_device_state_to_headers(self.headers)
        except:
            return False
        
        return True
    
    def check_link(self, url):
        if "https://" in url:
            url = url.replace("https://pay.paypay.ne.jp/", "")

        self.headers = PayPayUtils.set_baggage_to_headers(self.headers, PayPayUtils.SENTRY_PUBLIC, "0.0099999997764826", False, "P2PMoneyTransferDetailFragment", 0)

        _response = self.session.get(
            "https://app4.paypay.ne.jp/bff/v2/getP2PLinkInfo",
            params={
                "verificationCode": url,
                "payPayLang": "ja"
            },
            headers=self.headers
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return None
        except:
            return None
        
        self.bypass()
        
        return response
        
    def accept_link(self, url, passcode=None):
        if "https://" in url:
            url = url.replace("https://pay.paypay.ne.jp/", "")

        info = self.check_link(url)
        if info == None:
            return False
        elif info["payload"]["orderStatus"] != "PENDING":
            return False
        
        self.headers = PayPayUtils.set_baggage_to_headers(self.headers, PayPayUtils.SENTRY_PUBLIC, None, None, None, None)

        payload = {
            "requestId":str(uuid.uuid4()),
            "orderId": info["payload"]["pendingP2PInfo"]["orderId"],
            "verificationCode": url,
            "passcode": None,
            "senderMessageId": info["payload"]["message"]["messageId"],
            "senderChannelUrl": info["payload"]["message"]["chatRoomId"]
        }

        if info["payload"]["pendingP2PInfo"]["isSetPasscode"]:
            payload["passcode"] = passcode

        _response = self.session.post(
            "https://app4.paypay.ne.jp/bff/v2/acceptP2PSendMoneyLink",
            params=self.params,
            headers=self.headers,
            json=payload
        )
        try:
            response = _response.json()
            if response["header"]["resultCode"] != "S0000":
                return False
        except:
            return False
        
        self.bypass()
        
        return True
    
    def bypass(self):
        self.headers = PayPayUtils.set_baggage_to_headers(self.headers, PayPayUtils.SENTRY_PUBLIC, 0.0099999997764826, False, "MainActivity", 0)
        
        self.session.get(
            "https://app4.paypay.ne.jp/bff/v1/getGlobalServiceStatus",
            params={
                "payPayLang": "en"
            },
            headers=self.headers
        )
        
        self.session.post(
            "https://app4.paypay.ne.jp/bff/v3/getHomeDisplayInfo",
            params={
                "payPayLang": "ja"
            },
            headers=self.headers,
            json={
                "excludeMissionBannerInfoFlag": False,
                "includeBeginnerFlag": False,
                "includeSkinInfoFlag": False,
                "networkStatus": "WIFI"
            }
        )

        self.session.get(
            "https://app4.paypay.ne.jp/bff/v1/getSearchBar?payPayLang=ja",
            params={
                "payPayLang": "ja"
            },
            headers=self.headers
        )