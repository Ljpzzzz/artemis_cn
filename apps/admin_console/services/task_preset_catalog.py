# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Preset Task Catalog & Dynamic Recommendation Engine for Artemis."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class AppInfo(BaseModel):
    """Application metadata."""

    name: str
    icon: str
    pkg: str
    category: str = "general"


class TaskPreset(BaseModel):
    """Smart suggestion task definition."""

    id: str
    title: str
    description: str
    goal: str
    profile: Literal["flash", "pro"]
    category: Literal["flash", "pro", "cross_app", "monitor"]
    tag: str
    apps: list[AppInfo]
    required_packages: list[str] = Field(default_factory=list)
    match_mode: Literal["any", "all"] = "any"
    priority: int = 50


# ============================================================================
# APP PACKAGE REGISTRY
# ============================================================================

APP_REGISTRY: dict[str, dict[str, str]] = {
    # Google Suite & System
    "com.google.android.apps.maps": {"name": "Maps", "icon": "explore", "category": "navigation"},
    "com.google.android.gm": {"name": "Gmail", "icon": "mail", "category": "productivity"},
    "com.android.chrome": {"name": "Chrome", "icon": "public", "category": "browser"},
    "com.google.android.youtube": {
        "name": "YouTube",
        "icon": "smart_display",
        "category": "entertainment",
    },
    "com.android.settings": {"name": "Settings", "icon": "settings", "category": "system"},
    "com.google.android.deskclock": {"name": "Clock", "icon": "timer", "category": "utility"},
    "com.android.deskclock": {"name": "Clock", "icon": "timer", "category": "utility"},
    "com.google.android.calculator": {
        "name": "Calculator",
        "icon": "calculate",
        "category": "utility",
    },
    "com.android.calculator2": {"name": "Calculator", "icon": "calculate", "category": "utility"},
    "com.google.android.apps.photos": {
        "name": "Photos",
        "icon": "photo_library",
        "category": "media",
    },
    "com.google.android.calendar": {
        "name": "Calendar",
        "icon": "calendar_month",
        "category": "productivity",
    },
    "com.google.android.keep": {
        "name": "Keep Notes",
        "icon": "note_alt",
        "category": "productivity",
    },
    "com.android.vending": {"name": "Play Store", "icon": "storefront", "category": "tools"},
    "com.google.android.apps.messaging": {
        "name": "Messages",
        "icon": "chat",
        "category": "communication",
    },
    # Popular Ecosystem Apps
    "com.tencent.mm": {"name": "WeChat", "icon": "forum", "category": "social"},
    "com.xingin.xhs": {"name": "Xiaohongshu", "icon": "auto_stories", "category": "social"},
    "com.sankuai.meituan": {"name": "Meituan", "icon": "restaurant", "category": "lifestyle"},
    "com.dianping.v1": {"name": "Dianping", "icon": "star", "category": "lifestyle"},
    "tv.danmaku.bili": {"name": "Bilibili", "icon": "video_library", "category": "entertainment"},
    "com.eg.android.AlipayGphone": {
        "name": "Alipay",
        "icon": "account_balance_wallet",
        "category": "finance",
    },
    "com.netease.cloudmusic": {
        "name": "NetEase Music",
        "icon": "headphones",
        "category": "entertainment",
    },
    "com.spotify.music": {"name": "Spotify", "icon": "music_note", "category": "entertainment"},
}


# ============================================================================
# CURATED TASK PRESET LIBRARY (1-2 curated tasks per common app)
# ============================================================================

PRESET_TASK_CATALOG: list[TaskPreset] = [
    # 1. Google Maps
    TaskPreset(
        id="maps_coffee",
        title="寻找精品咖啡",
        description="在 Google 地图中搜索附近评分最高的咖啡馆",
        goal="打开 Google 地图，搜索附近评分最高的精品咖啡店，并查看第一条结果的详情。",
        profile="flash",
        category="flash",
        tag="Maps",
        apps=[
            AppInfo(
                name="Maps",
                icon="explore",
                pkg="com.google.android.apps.maps",
                category="navigation",
            )
        ],
        required_packages=["com.google.android.apps.maps"],
        priority=95,
    ),
    TaskPreset(
        id="pro_commute_share",
        title="通勤时间预估与消息草稿",
        description="在地图中查看通勤时间，并在信息中草拟到达时间",
        goal="打开 Google 地图查看前往国际机场的通勤时间，计算到达时间，然后打开信息应用草拟一条包含预计到达时间的短信。",
        profile="pro",
        category="cross_app",
        tag="Maps + Messages",
        apps=[
            AppInfo(
                name="Maps",
                icon="explore",
                pkg="com.google.android.apps.maps",
                category="navigation",
            ),
            AppInfo(
                name="Messages",
                icon="chat",
                pkg="com.google.android.apps.messaging",
                category="communication",
            ),
        ],
        required_packages=["com.google.android.apps.maps", "com.google.android.apps.messaging"],
        match_mode="all",
        priority=92,
    ),
    # 2. Gmail
    TaskPreset(
        id="gmail_receipts",
        title="搜索订单收据",
        description="在 Gmail 中查找最近的航班或配送确认邮件",
        goal="打开 Gmail，搜索最近的航班或包裹配送确认邮件。",
        profile="flash",
        category="flash",
        tag="Gmail",
        apps=[
            AppInfo(name="Gmail", icon="mail", pkg="com.google.android.gm", category="productivity")
        ],
        required_packages=["com.google.android.gm"],
        priority=90,
    ),
    TaskPreset(
        id="pro_email_to_calendar",
        title="将行程邮件添加到日历",
        description="从 Gmail 提取航班或活动日期并安排到日历",
        goal="打开 Gmail 查找最新的活动邀请或行程单，提取日期和地点，然后打开 Google 日历创建对应的日程事件。",
        profile="pro",
        category="cross_app",
        tag="Gmail + Calendar",
        apps=[
            AppInfo(
                name="Gmail", icon="mail", pkg="com.google.android.gm", category="productivity"
            ),
            AppInfo(
                name="Calendar",
                icon="calendar_month",
                pkg="com.google.android.calendar",
                category="productivity",
            ),
        ],
        required_packages=["com.google.android.gm"],
        priority=94,
    ),
    # 3. Chrome
    TaskPreset(
        id="chrome_research",
        title="搜索 AI 领域最新突破",
        description="在 Chrome 浏览器中搜索最新的多模态 AI 进展",
        goal="打开 Chrome 浏览器，搜索多模态移动端 AI 智能体的最新突破。",
        profile="flash",
        category="flash",
        tag="Chrome",
        apps=[AppInfo(name="Chrome", icon="public", pkg="com.android.chrome", category="browser")],
        required_packages=["com.android.chrome"],
        priority=88,
    ),
    TaskPreset(
        id="pro_research_keep",
        title="产品调研与笔记记录",
        description="在 Chrome 比较前三名耳机并在 Keep 中记录对比",
        goal="打开 Chrome，调研排名前三的降噪耳机，对比价格和续航，然后在 Keep 笔记中写一条结构化的对比总结笔记。",
        profile="pro",
        category="pro",
        tag="Chrome + Keep",
        apps=[
            AppInfo(name="Chrome", icon="public", pkg="com.android.chrome", category="browser"),
            AppInfo(
                name="Keep Notes",
                icon="note_alt",
                pkg="com.google.android.keep",
                category="productivity",
            ),
        ],
        required_packages=["com.android.chrome"],
        priority=91,
    ),
    # 4. YouTube
    TaskPreset(
        id="youtube_lofi",
        title="播放 Lo-Fi 音乐电台",
        description="在 YouTube 搜索并播放 Lo-Fi 嘻哈直播",
        goal="打开 YouTube，搜索「Lofi hip hop beats relaxing radio」，然后点击直播流。",
        profile="flash",
        category="flash",
        tag="YouTube",
        apps=[
            AppInfo(
                name="YouTube",
                icon="smart_display",
                pkg="com.google.android.youtube",
                category="entertainment",
            )
        ],
        required_packages=["com.google.android.youtube"],
        priority=85,
    ),
    # 5. Settings
    TaskPreset(
        id="settings_display_wifi",
        title="深色模式与 Wi-Fi 检查",
        description="在设置中切换深色主题并验证网络连接",
        goal="打开设置应用，进入显示设置，确保已开启深色主题，并检查 Wi-Fi 连接状态。",
        profile="flash",
        category="flash",
        tag="Settings",
        apps=[
            AppInfo(name="Settings", icon="settings", pkg="com.android.settings", category="system")
        ],
        required_packages=["com.android.settings"],
        priority=87,
    ),
    TaskPreset(
        id="pro_settings_qa",
        title="子系统健康与崩溃探测",
        description="遍历设置子菜单以验证屏幕并检查崩溃对话框",
        goal="遍历设置子菜单（网络、已连接设备、应用、电池、存储），确认每个页面都能正常加载且没有 ANR 或崩溃弹窗，并汇总结果。",
        profile="pro",
        category="monitor",
        tag="Settings QA",
        apps=[
            AppInfo(name="Settings", icon="settings", pkg="com.android.settings", category="system")
        ],
        required_packages=["com.android.settings"],
        priority=93,
    ),
    # 6. Clock
    TaskPreset(
        id="clock_timer",
        title="25 分钟番茄钟",
        description="在时钟应用中启动 25 分钟专注倒计时",
        goal="打开时钟应用，切换到计时器标签页，设置 25 分钟并启动倒计时。",
        profile="flash",
        category="flash",
        tag="Clock",
        apps=[
            AppInfo(
                name="Clock", icon="timer", pkg="com.google.android.deskclock", category="utility"
            )
        ],
        required_packages=["com.google.android.deskclock", "com.android.deskclock"],
        priority=86,
    ),
    # 7. Calculator
    TaskPreset(
        id="calc_gratuity",
        title="分摊账单并计算小费",
        description="在计算器应用中计算 3 人 186.40 美元账单的 18% 小费",
        goal="打开计算器，计算 186.40 美元账单的 18% 小费，再除以 3 人。",
        profile="flash",
        category="flash",
        tag="Calculator",
        apps=[
            AppInfo(
                name="Calculator",
                icon="calculate",
                pkg="com.google.android.calculator",
                category="utility",
            )
        ],
        required_packages=["com.google.android.calculator", "com.android.calculator2"],
        priority=84,
    ),
    # 8. Photos
    TaskPreset(
        id="photos_inspect",
        title="查看最近截图",
        description="打开 Google 相册查看最新截图",
        goal="打开 Google 相册，查看「截图」相册中最新的一张截图。",
        profile="flash",
        category="flash",
        tag="Photos",
        apps=[
            AppInfo(
                name="Photos",
                icon="photo_library",
                pkg="com.google.android.apps.photos",
                category="media",
            )
        ],
        required_packages=["com.google.android.apps.photos"],
        priority=82,
    ),
    # 9. WeChat
    TaskPreset(
        id="wechat_browse",
        title="查看微信消息",
        description="打开微信查看最近的聊天会话",
        goal="打开微信，查看最上方的最近聊天消息。",
        profile="flash",
        category="flash",
        tag="WeChat",
        apps=[AppInfo(name="WeChat", icon="forum", pkg="com.tencent.mm", category="social")],
        required_packages=["com.tencent.mm"],
        priority=89,
    ),
    TaskPreset(
        id="pro_wechat_to_calendar",
        title="微信通知转日历",
        description="从微信聊天中提取会议通知并添加到日历",
        goal="打开微信，在最上方的聊天中找到最新的会议通知或活动消息，提取时间和主题，然后打开日历安排一个日程。",
        profile="pro",
        category="cross_app",
        tag="WeChat + Calendar",
        apps=[
            AppInfo(name="WeChat", icon="forum", pkg="com.tencent.mm", category="social"),
            AppInfo(
                name="Calendar",
                icon="calendar_month",
                pkg="com.google.android.calendar",
                category="productivity",
            ),
        ],
        required_packages=["com.tencent.mm"],
        priority=93,
    ),
    # 10. Xiaohongshu
    TaskPreset(
        id="xhs_coffee_guide",
        title="小红书咖啡攻略搜索",
        description="在小红书搜索热门精品咖啡馆点评",
        goal="打开小红书，搜索评分最高的精品咖啡店，并查看第一条帖子。",
        profile="flash",
        category="flash",
        tag="Xiaohongshu",
        apps=[
            AppInfo(
                name="Xiaohongshu", icon="auto_stories", pkg="com.xingin.xhs", category="social"
            )
        ],
        required_packages=["com.xingin.xhs"],
        priority=87,
    ),
    # 11. Meituan / Dianping
    TaskPreset(
        id="meituan_ramen_search",
        title="美团美食搜索",
        description="在美团或大众点评搜索附近评分最高的拉面",
        goal="打开美团或大众点评，搜索附近评分最高的拉面，并查看排名第一的餐厅评分。",
        profile="flash",
        category="flash",
        tag="Meituan",
        apps=[
            AppInfo(
                name="Meituan", icon="restaurant", pkg="com.sankuai.meituan", category="lifestyle"
            )
        ],
        required_packages=["com.sankuai.meituan", "com.dianping.v1"],
        priority=86,
    ),
    # 12. Bilibili
    TaskPreset(
        id="bilibili_stream",
        title="Bilibili 科技视频",
        description="在 Bilibili 搜索并播放 AI 智能体教程视频",
        goal="打开 Bilibili，搜索「AI Agent Architecture」，并播放匹配度最高的视频。",
        profile="flash",
        category="flash",
        tag="Bilibili",
        apps=[
            AppInfo(
                name="Bilibili",
                icon="video_library",
                pkg="tv.danmaku.bili",
                category="entertainment",
            )
        ],
        required_packages=["tv.danmaku.bili"],
        priority=85,
    ),
    # 13. Play Store
    TaskPreset(
        id="pro_playstore_review",
        title="应用商店评论研究",
        description="在 Google Play 比较热门任务管理应用及评分",
        goal="打开 Google Play 商店，搜索评分最高的任务管理应用，对比排名前两位应用的评分和最新用户评论，并记录推荐结论。",
        profile="pro",
        category="pro",
        tag="Play Store",
        apps=[
            AppInfo(
                name="Play Store", icon="storefront", pkg="com.android.vending", category="tools"
            )
        ],
        required_packages=["com.android.vending"],
        priority=88,
    ),
]


# ============================================================================
# RECOMMENDATION ENGINE
# ============================================================================


class TaskRecommendationEngine:
    """Intelligent recommendation engine matching device capabilities."""

    def __init__(self, catalog: list[TaskPreset] | None = None):
        self.catalog = catalog or PRESET_TASK_CATALOG

    def get_all_tasks(self) -> list[dict[str, Any]]:
        return [task.model_dump() for task in self.catalog]

    def recommend_tasks(
        self, installed_packages: list[str] | set[str], category: str = "all", limit: int = 12
    ) -> list[dict[str, Any]]:
        pkgs_set = (
            set(installed_packages) if isinstance(installed_packages, list) else installed_packages
        )

        scored_tasks: list[tuple[int, TaskPreset, bool]] = []

        for task in self.catalog:
            # Check package presence
            is_matched = False
            if pkgs_set:
                if not task.required_packages:
                    is_matched = True
                elif task.match_mode == "all":
                    is_matched = all(pkg in pkgs_set for pkg in task.required_packages)
                else:
                    is_matched = any(pkg in pkgs_set for pkg in task.required_packages)
            else:
                is_matched = False

            # Calculate score
            score = task.priority
            if pkgs_set:
                if is_matched:
                    score += 100
                    if len(task.required_packages) > 1 and task.match_mode == "all":
                        score += 30
                else:
                    score -= 40

            # Filter by category
            if category == "flash" and task.profile != "flash":
                continue
            elif category == "pro" and task.profile != "pro":
                continue
            elif category == "cross_app" and task.category != "cross_app":
                continue
            elif category == "monitor" and task.category != "monitor":
                continue

            scored_tasks.append((score, task, is_matched))

        # Sort descending by score
        scored_tasks.sort(key=lambda item: item[0], reverse=True)

        results: list[dict[str, Any]] = []
        for _, task, matched in scored_tasks[:limit]:
            d = task.model_dump()
            d["is_device_matched"] = matched
            results.append(d)

        return results


task_recommendation_engine = TaskRecommendationEngine()
