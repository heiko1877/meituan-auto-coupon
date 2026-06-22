#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美团自动领券脚本 - GitHub Actions 版（真实可用）
"""

import json
import os
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

TOKEN = os.environ.get("MEITUAN_TOKEN", "")

# 真实领券接口（从美团助手源码提取）
API_URL = "https://media.meituan.com/fulishemini/couponActivity/sendCouponWork"

# ============================================================
# 核心逻辑
# ============================================================

def fen_to_yuan(fen):
    """分转元"""
    if not fen:
        return "0"
    yuan = int(fen) / 100
    return str(int(yuan)) if yuan == int(yuan) else f"{yuan:.1f}"


def format_coupon(c):
    """格式化券信息"""
    name = c.get("couponName", "")
    price_limit = c.get("priceLimit", 0)
    coupon_value = c.get("couponValue", 0)
    
    if price_limit and price_limit > 0:
        discount = f"满{fen_to_yuan(price_limit)}元减{fen_to_yuan(coupon_value)}元"
    else:
        discount = f"减{fen_to_yuan(coupon_value)}元"
    
    # 格式化有效期
    start = c.get("couponStartTime", 0)
    end = c.get("couponEndTime", 0)
    if start and end:
        start_str = datetime.fromtimestamp(start / 1000).strftime("%Y-%m-%d")
        end_str = datetime.fromtimestamp(end / 1000).strftime("%Y-%m-%d")
        valid_period = f"{start_str} 至 {end_str}"
    else:
        valid_period = "未知"
    
    return {
        "name": name,
        "discount_info": discount,
        "valid_period": valid_period,
        "tab_name": c.get("tabName", ""),
    }


def claim_coupons():
    """领取优惠券"""
    if not TOKEN:
        print("❌ 未配置 MEITUAN_TOKEN，请在 GitHub Secrets 中添加")
        return {"status": "no_token"}
    
    print(f"🔑 使用 Token: {TOKEN[:8]}****")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    payload = {
        "token": TOKEN,
        "aiScene": "",
        "version": 2,
    }
    
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
                    formatted = format_coupon(c)
                    print(f"      🎟️  {formatted['name']} - {formatted['discount_info']}")
                    print(f"         有效期：{formatted['valid_period']}")
                
                return {
                    "status": "success",
                    "coupon_count": len(coupon_list),
                    "coupons": [format_coupon(c) for c in coupon_list],
                    "activity_name": activity_name,
                }
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
            
    except requests.exceptions.Timeout:
        print(f"   ⏱ 请求超时")
        return {"status": "timeout"}
    except Exception as e:
        print(f"   ❌ 异常：{str(e)}")
        return {"status": "error", "error": str(e)}


def main():
    """主函数"""
    print("=" * 50)
    print(f"🚀 美团自动领券 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    result = claim_coupons()
    
    print("\n" + "=" * 50)
    print("📊 本次运行结果")
    print("=" * 50)
    
    status_icon = {
        "success": "✅",
        "already_received": "ℹ️ ",
        "empty": "📭",
        "auth_failed": "🔑",
        "failed": "❌",
        "timeout": "⏱",
        "error": "💥",
        "no_token": "❌",
    }.get(result["status"], "❓")
    
    print(f"  {status_icon} {result.get('message', result.get('coupon_count', '完成'))}")
    
    if result.get("status") == "success":
        print(f"\n🎉 共成功领取 {result['coupon_count']} 张优惠券")
    
    # 保存结果
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump({
            "time": datetime.now().isoformat(),
            "result": result,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存到 result.json")


if __name__ == "__main__":
    main()
