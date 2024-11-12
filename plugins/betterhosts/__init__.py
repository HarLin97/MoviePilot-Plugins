from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

class BetterHosts(_PluginBase):
    # 插件名称
    plugin_name = "更好的hosts"
    # 插件描述
    plugin_desc = "自动更新系统hosts文件，解决DNS污染问题。"
    # 插件图标
    plugin_icon = "betterhosts.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "HarLin97"
    # 作者主页
    author_url = "https://github.com/HarLin97"
    # 插件配置项ID前缀
    plugin_config_prefix = "betterhosts_"
    # 加载顺序
    plugin_order = 10
    # 可使用的用户级别
    auth_level = 1

    _enabled = False
    _domain_list = ["api.themoviedb.org", "image.tmdb.org"]
    _github_host_url = "https://hosts.gitcdn.top/hosts.txt"
    _dns_api = "https://networkcalc.com/api/dns/lookup"
    _scheduler = None
    _schedule_interval = None

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            custom_domains = config.get("domain_list", "")
            self._domain_list = custom_domains.split() if custom_domains else self._domain_list
            self._schedule_interval = config.get("schedule_interval", "1hour")  # 默认1小时

            if self._enabled:
                self.update_hosts()
                self.setup_scheduler()
            else:
                self.__clear_system_hosts()

    def stop_service(self):
        """
        停用插件时清除系统hosts中由插件添加的记录
        """
        if self._scheduler:
            self._scheduler.shutdown()
        self.__clear_system_hosts()
        logger.info("插件已禁用，清理自定义hosts记录。")

    def setup_scheduler(self):
        """
        设置定时任务，根据用户选择的频率来更新hosts
        """
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler()

        interval = None
        if self._schedule_interval == "1hour":
            interval = IntervalTrigger(hours=1)
        elif self._schedule_interval == "1day":
            interval = IntervalTrigger(days=1)
        elif self._schedule_interval == "1week":
            interval = IntervalTrigger(weeks=1)

        if interval:
            self._scheduler.add_job(self.update_hosts, interval)
            self._scheduler.start()
            logger.info(f"定时任务已启动，更新频率: {self._schedule_interval}")

    def update_hosts(self):
        """
        根据DNS API查询域名IP，更新系统hosts文件
        """
        hosts_content = []
        error_domains = []
        system_hosts = self.__read_system_hosts()

        # 从 GitHub 获取 hosts 文件
        try:
            github_hosts = requests.get(self._github_host_url).text
            # 将 GitHub 的 hosts 内容添加到系统 hosts
            hosts_content.append(github_hosts)
        except Exception as e:
            logger.error(f"无法获取 GitHub hosts 文件: {e}")

        # 从 DNS API 获取每个域名的 IP 地址并添加到 hosts 文件
        for domain in self._domain_list:
            try:
                response = requests.get(f"{self._dns_api}/{domain}")
                ip_addresses = [entry['address'] for entry in response.json().get("records", {}).get("A", [])]
                for ip in ip_addresses:
                    hosts_content.append(f"{ip}\t{domain}")
            except Exception as e:
                logger.error(f"无法获取{domain}的IP: {e}")
                error_domains.append(domain)

        # 更新hosts文件
        if hosts_content:
            self.__write_hosts(system_hosts, hosts_content)
        else:
            logger.info("没有需要更新的hosts记录。")

    def __write_hosts(self, system_hosts, hosts_content):
        """
        写入hosts文件
        """
        try:
            with open("/etc/hosts", "a") as f:
                f.write("# BetterHostsPlugin\n")
                f.write("\n".join(hosts_content))
                f.write("\n# BetterHostsPlugin End\n")
            logger.info("hosts文件更新成功。")
        except Exception as e:
            logger.error(f"更新hosts文件失败: {e}")

    def __clear_system_hosts(self):
        """
        清除插件添加的hosts记录
        """
        try:
            with open("/etc/hosts", "r") as f:
                lines = f.readlines()
            with open("/etc/hosts", "w") as f:
                write = True
                for line in lines:
                    if line.strip() == "# BetterHostsPlugin":
                        write = False
                    elif line.strip() == "# BetterHostsPlugin End":
                        write = True
                    elif write:
                        f.write(line)
            logger.info("清除插件hosts记录成功。")
        except Exception as e:
            logger.error(f"清除hosts文件失败: {e}")
    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'domain_list',
                                            'label': '自定义域名',
                                            'rows': 5,
                                            'placeholder': '输入自定义域名，每行一个'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'schedule_interval',
                                            'label': '定时更新频率',
                                            'items': [
                                                {'text': '1小时', 'value': '1hour'},
                                                {'text': '1天', 'value': '1day'},
                                                {'text': '1周', 'value': '1week'}
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "domain_list": "",
            "schedule_interval": "1hour"  # 默认1小时
        }
