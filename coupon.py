#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美团自动领券脚本 - GitHub Actions 版（真实可用）
"""

import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install requests")
    sys.exit(1)

TOKEN = os.environ.get("MEITUAN_TOKEN", "")
API_URL = "https://media.meituan.com/fulishemini/couponActivity/sendCouponWork"

def fen_to_yuan(fen):
    if not fen:
        return "0"
    yuan = int(fen) / 100
    return str(int(yuan)) if yuan == int(yuan) else f"{yuan:.1f}"

def claim_coupons():
    if not TOKEN:
        print("❌ 未配置 MEITUAN_TOKEN，请在 GitHub Secrets 中添加")
        return {"status": "no_token"}

    print(f"🔑 Token 已配置")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {"token": TOKEN, "aiScene": "", "version": 2}

    try:
        print(f"\n{'='*40}")
        print("🎫 正在领取美团优惠券...")
        print(f"   接口：{API_URL}")

        resp = requests.post(API_URL, json=payload, headers=headers, timeout=15)
        data = resp.json()

        code = data.get("code", -1)
        msg = data.get("msg", "")

        if code == 200:
            coupon_list = data.get("data", {}).get("couponList", [])
            activity_name = data.get("data", {}).get("activityName", "")

            if coupon_list:
                print(f"   ✅ 成功！领取到 {len(coupon_list)} 张优惠券")
                print(f"\n   📋 券详情：")
                for c in coupon_list:
                    name = c.get("couponName", "")
                    price_limit = c.get("priceLimit", 0)
                    coupon_value = c.get("couponValue", 0)
                    if price_limit > 0:
                        discount = f"满{fen_to_yuan(price_limit)}元减{fen_to_yuan(coupon_value)}元"
                    else:
                        discount = f"减{fen_to_yuan(coupon_value)}元"
                    print(f"      🎟️  {name} - {discount}")

                return {"status": "success", "coupon_count": len(coupon_list)}
            else:
                print(f"   ⚠️  接口正常，但暂无可领券")
                return {"status": "empty", "message": "暂无可领券"}
        elif code == 1014:
            print(f"   ℹ️  今日已领过")
            return {"status": "already_received", "message": "今日已领取"}
        elif code == 401:
            print(f"   ❌ 登录失效！请更新 MEITUAN_TOKEN")
            return {"status": "auth_failed", "message": "Token 已过期"}
        else:
            print(f"   ❌ 失败：{code} - {msg}")
            return {"status": "failed", "code": code, "message": msg}
    except Exception as e:
        print(f"   ❌ 异常：{str(e)}")
        return {"status": "error", "error": str(e)}

def main():
    print("=" * 50)
    print(f"🚀 美团自动领券 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    result = claim_coupons()

    status_icon = {"success": "✅", "already_received": "ℹ️ ", "empty": "📭",
                   "auth_failed": "🔑", "failed": "❌", "error": "💥",
                   "no_token": "❌"}.get(result["status"], "❓")
    print(f"\n{status_icon} {result.get('message', result.get('coupon_count', '完成'))}")

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump({"time": datetime.now().isoformat(), "result": result}, f,
                  ensure_ascii=False, indent=2)
    print("\n💾 结果已保存到 result.json")

if __name__ == "__main__":
    main()
