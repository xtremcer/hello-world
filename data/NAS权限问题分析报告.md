# NAS挂载权限问题分析报告

## 问题现象
重启后运行股票脚本，出现权限错误：
```
❌ 提权失败：[Errno 1] Operation not permitted: '/mnt/nas/stock/data'
❌ 无目录写入权限，程序退出
```

## 问题根因分析

### 1. 双重挂载机制冲突

系统存在两套挂载机制：

1. **systemd automount** (自动触发)
   - 由 `/etc/fstab` 中 `x-systemd.automount` 自动生成
   - 挂载选项：`uid=0,gid=0,file_mode=0755,dir_mode=0755,noforceuid,noforcegid`
   
2. **手动挂载** (成功覆盖)
   - 我们手动执行mount命令
   - 挂载选项：`uid=1000,gid=1000,file_mode=0777,dir_mode=0777`

**问题**：重启后systemd优先使用automount，用的是低权限配置(0755)，覆盖了高权限配置(0777)。

### 2. _netdev参数未能解决问题

添加 `_netdev` 期望等待网络就绪，但systemd仍然在网络不完全就绪时触发挂载，导致权限配置失败。

### 3. cron任务执行时的问题

- cron任务在每天16:00执行
- 如果挂载在16:00前未完全就绪，会使用错误的低权限配置
- 脚本无法写入目录，直接失败（无错误输出到日志）

## 当前状态

刚才手动重新挂载后，权限已恢复正常（uid=1000, dir_mode=0777）。

## 解决方案

### 方案：使用systemd管理挂载（推荐）

创建专门的systemd挂载单元，确保网络依赖正确配置：

```bash
sudo tee /etc/systemd/system/mnt-nas-mount.service << 'EOF'
[Unit]
Description=NAS mount for /mnt/nas
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/mount -t cifs //192.168.192.168/test /mnt/nas -o username=timi,password=beinimadeshi,iocharset=utf8,vers=2.0,uid=1000,gid=1000,file_mode=0777,dir_mode=0777,noperm
ExecStop=/bin/umount /mnt/nas

[Install]
WantedBy=multi-user.target
EOF
```

然后：
```bash
sudo systemctl daemon-reload
sudo systemctl enable mnt-nas-mount.service
```

同时修改fstab，注释掉NAS行（避免systemd自动生成automount）：
```
# //192.168.192.168/test /mnt/nas cifs ... (注释掉)
```

### 方案2：继续观察

如果方案1太复杂，可以先继续观察。当前手动挂载后权限正常，cron任务可能在网络更稳定的时间点（16:00）能正常工作。

## 建议

1. 先用方案1彻底解决问题
2. 如果暂时不想改，可以记录：每次重启后检查权限，必要时手动 `sudo mount -o remount /mnt/nas`