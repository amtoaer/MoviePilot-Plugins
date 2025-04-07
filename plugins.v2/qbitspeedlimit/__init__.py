from typing import List, Tuple, Dict, Any
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType, ServiceInfo
from apscheduler.triggers.cron import CronTrigger
from app.helper.downloader import DownloaderHelper


class QbitSpeedLimit(_PluginBase):
    # 插件名称
    plugin_name = "QB定时限速"
    # 插件描述
    plugin_desc = "QB定时限速"
    # 插件图标
    plugin_icon = "Qbittorrent_B.png"
    # 插件版本
    plugin_version = "2.0"
    # 插件作者
    plugin_author = "amtoaer"
    # 作者主页
    author_url = "https://github.com/amtoaer"
    # 插件配置项ID前缀
    plugin_config_prefix = "qbit_speed_limit"
    # 加载顺序
    plugin_order = 1
    # 可使用的用户级别
    auth_level = 1

    _enabled: bool = False
    _notify: bool = False
    _pause_cron = None
    _resume_cron = None
    _enable_upload_limit = False
    _pause_upload_limit = None
    _resume_upload_limit = None
    _enable_download_limit = False
    _pause_download_limit = None
    _resume_download_limit = None
    _downloaders = None

    def init_plugin(self, config: dict = None):
        self.downloader_helper = DownloaderHelper()
        self.stop_service()
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._pause_cron = config.get("pause_cron")
            self._resume_cron = config.get("resume_cron")
            self._enable_download_limit = config.get("enable_download_limit")
            self._pause_download_limit = config.get("pause_download_limit")
            self._resume_download_limit = config.get("resume_download_limit")
            self._enable_upload_limit = config.get("enable_upload_limit")
            self._pause_upload_limit = config.get("pause_upload_limit")
            self._resume_upload_limit = config.get("resume_upload_limit")
            self._downloaders = config.get("downloaders")

    @property
    def available_qbittorrents(self) -> List[ServiceInfo]:
        qbits = []
        if not (
            self._downloaders
            and (
                services := self.downloader_helper.get_services(
                    name_filters=self._downloaders
                )
            )
        ):
            return qbits
        for _, service_info in services.items():
            if not service_info.instance.is_inactive() and self.check_is_qb(
                service_info
            ):
                qbits.append(service_info)
        return qbits

    def check_is_qb(self, service_info) -> bool:
        if self.downloader_helper.is_downloader(
            service_type="qbittorrent", service=service_info
        ):
            return True
        return False

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        if self._enabled and self._pause_cron and self._resume_cron:
            return [
                {
                    "id": "QbSpeedLimitPause",
                    "name": "暂停QB限速",
                    "trigger": CronTrigger.from_crontab(self._pause_cron),
                    "func": lambda: self.set_limit(
                        self._pause_upload_limit, self._pause_download_limit
                    ),
                    "kwargs": {},
                },
                {
                    "id": "QbSpeedLimitResume",
                    "name": "开始QB限速",
                    "trigger": CronTrigger.from_crontab(self._resume_cron),
                    "func": lambda: self.set_limit(
                        self._resume_upload_limit, self._resume_download_limit
                    ),
                    "kwargs": {},
                },
            ]
        return []

    def set_limit(self, upload_limit: int, download_limit: int) -> bool:
        if not (self._enable_upload_limit or self._enable_download_limit):
            return True
        ok = True
        for service in self.available_qbittorrents:
            download_obj = service.instance
            if not download_obj:
                logger.error(f"{self.LOG_TAG} 获取下载器失败 {service.name}")
                continue
            current_download_limit, current_upload_limit = (
                download_obj.get_speed_limit()
            )
            if not self._enable_download_limit:
                download_limit = current_download_limit
            if not self._enable_upload_limit:
                upload_limit = current_upload_limit
            try:
                download_limit, upload_limit = int(download_limit), int(upload_limit)
            except Exception as e:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="【QB定时限速】",
                    text=f"设置QB限速失败,限速不是一个数值: {e}",
                )
                logger.error(f"{self.LOG_TAG} 限速失败,限速不是一个数值: {e}")
                continue
            ok = ok and download_obj.set_speed_limit(
                download_limit=download_limit, upload_limit=upload_limit
            )
        return ok

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "notify",
                                            "label": "发送通知",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "multiple": True,
                                            "chips": True,
                                            "clearable": True,
                                            "model": "downloaders",
                                            "label": "下载器",
                                            "items": [
                                                {
                                                    "title": config.name,
                                                    "value": config.name,
                                                }
                                                for config in self.downloader_helper.get_configs().values()
                                            ],
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VCronField",
                                        "props": {
                                            "model": "pause_cron",
                                            "label": "暂停限速周期",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VCronField",
                                        "props": {
                                            "model": "resume_cron",
                                            "label": "开始限速周期",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enable_upload_limit",
                                            "label": "上传限速",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enable_download_limit",
                                            "label": "下载限速",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "pause_upload_limit",
                                            "label": "暂停时上传限速 KB/s",
                                            "placeholder": "KB/s",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "pause_download_limit",
                                            "label": "暂停时下载限速 KB/s",
                                            "placeholder": "KB/s",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "resume_upload_limit",
                                            "label": "开始时上传限速 KB/s",
                                            "placeholder": "KB/s",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "resume_download_limit",
                                            "label": "开始时下载限速 KB/s",
                                            "placeholder": "KB/s",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        ], {
            "enabled": False,
            "notify": True,
            "enable_download_limit": False,
            "pause_download_limit": 0,
            "resume_download_limit": 0,
            "enable_upload_limit": False,
            "pause_upload_limit": 0,
            "resume_upload_limit": 0,
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        pass
