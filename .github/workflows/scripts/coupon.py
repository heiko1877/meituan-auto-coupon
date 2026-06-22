#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美团自动领券脚本 - GitHub Actions 版本
支持：外卖红包、天天神券、闪购券等
"""

import json
import os
import re
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install requests")
    sys.exit(1)

# ============================================================
# 配置区
# ============================================================

# 从环境变量读取 Cookie 和 Token
COOKIE = os.environ.get("MEITUAN_COOKIE", "")
TOKEN = os.environ.get("MEITUAN_TOKEN", "")

# 请求头模板
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://h5.waimai.meituan.com",
    "Referer": "https://h5.waimai.meituan.com/",
}

# 领券接口列表（按优先级排序）
COUPON_ENDPOINTS = [
    {
        "name": "天天神券",
        "url": "https://apimobile.meituan.com/group/v1/promotion/coupon/receive",
        "method": "POST",
        "params": {
            "activityId": "shenquan_daily",
            "platform": "3",
            "partner": "162",
            "riskVersion": "4999_1",
            "utm_medium": "android",
            "utm_source": "meishi",
        },
    },
    {
        "name": "外卖红包",
        "url": "https://wmapi.meituan.com/api/v1/user/redpacket/daily/grab",
        "method": "GET",
        "params": {
            "userId": "",
            "platform": "3",
        },
    },
    {
        "name": "闪购券",
        "url": "https://apimobile.meituan.com/group/v1/shangou/coupon/receive",
        "method": "POST",
        "params": {
            "activityType": "daily",
            "platform": "3",
        },
    },
]

# ============================================================
# 核心逻辑
# ============================================================


def build_session():
    """构建带认证信息的请求会话"""
    session = requests.Session()
    session.headers.update(HEADERS)

    if COOKIE:
        session.headers["Cookie"] = COOKIE
    if TOKEN:
        session.headers["token"] = TOKEN

    return session


def receive_coupon(session, endpoint):
    """尝试领取单个优惠券"""
    name = endpoint["name"]
    url = endpoint["url"]
    method = endpoint.get("method", "GET").upper()
    params = dict(endpoint.get("params", {}))

    print(f"\n{'='*40}")
    print(f"🎫 正在领取：{name}")
    print(f"   接口：{url}")

    try:
        if method == "GET":
            resp = session.get(url, params=params, timeout=15)
        else:
            resp = session.post(url, json=params, timeout=15)

        # 尝试解析响应
        try:
            data = resp.json()
        except ValueError:
            data = {"raw_text": resp.text[:200]}

        # 判断结果
        code = data.get("code", -1)
        msg = data.get("message", data.get("msg", ""))

        if code == 0 or data.get("success") or data.get("ok"):
            coupon_count = len(data.get("coupons", []))
            if coupon_count > 0:
                print(f"   ✅ 成功！领取到 {coupon_count} 张优惠券")
                for c in data.get("coupons", []):
                    print(f"      📌 {c.get('name', '未知')} - {c.get('discountInfo', '')}")
                return {"status": "success", "name": name, "coupon_count": coupon_count}
            else:
                print(f"   ⚠️  接口正常，但暂无可领券")
                return {"status": "empty", "name": name, "message": "暂无可领券"}
        elif code == 1014 or "已领" in str(msg) or "已经" in str(msg):
            print(f"   ℹ️  今日已领过")
            return {"status": "already_received", "name": name, "message": str(msg)}
        elif code == 401 or "登录" in str(msg) or "过期" in str(msg):
            print(f"   ❌ 登录失效！请更新 Cookie 或 Token")
            return {"status": "auth_failed", "name": name, "message": str(msg)}
        else:
            print(f"   ❌ 失败：{code} - {msg}")
            return {"status": "failed", "name": name, "code": code, "message": str(msg)}

    except requests.exceptions.Timeout:
        print(f"   ⏱ 请求超时")
        return {"status": "timeout", "name": name}
    except Exception as e:
        print(f"   ❌ 异常：{str(e)}")
        return {"status": "error", "name": name, "error": str(e)}


def main():
    """主函数"""
    print("=" * 50)
    print(f"🚀 美团自动领券 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 检查认证信息
    if not COOKIE and not TOKEN:
        result = {
            "status": "no_auth",
            "time": datetime.now().isoformat(),
            "message": "❌ 未配置 MEITUAN_COOKIE 或 MEITUAN_TOKEN，请在 GitHub Secrets 中添加"
        }
        print(result["message"])
        save_result(result)
        sys.exit(1)

    print(f"✅ 认证信息：{'Cookie' if COOKIE else 'Token'} 已配置")

    # 构建会话
    session = build_session()

    # 依次尝试各领券接口
    results = []
    success_count = 0
    for endpoint in COUPON_ENDPOINTS:
        result = receive_coupon(session, endpoint)
        results.append(result)

        if result.get("status") == "success":
            success_count += 1

        # 避免请求过快
        time.sleep(1)

    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 本次运行汇总")
    print("=" * 50)

    for r in results:
        status_icon = {
            "success": "✅",
            "already_received": "ℹ️ ",
            "empty": "📭",
            "auth_failed": "🔑",
            "failed": "❌",
            "timeout": "⏱",
            "error": "💥",
        }.get(r["status"], "❓")
        print(f"  {status_icon} {r['name']}: {r.get('message', r.get('coupon_count', '完成'))}")

    print(f"\n🎉 共成功领取 {success_count} 类优惠券")

    # 保存结果（供 Actions 日志使用）
    final_result = {
        "time": datetime.now().isoformat(),
        "total_success": success_count,
        "results": results,
    }
    save_result(final_result)


def save_result(data):
    """保存运行结果到文件"""
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
