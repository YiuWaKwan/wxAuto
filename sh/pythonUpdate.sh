# cmd命令窗口的快速编辑模式需要先关闭：右击命令窗口顶部->默认值->选项->快速编辑模式（Q） 把打勾去掉
python -m pip install --upgrade pip    -- pip 更新
pip install -U uiautomator2                 -- U2 更新   需要谨慎，确认后才更新
pip install -U weditor                    -- weditor 更新  与u2匹配
pip install -U Pillow                             -- Pillow 更新  与u2匹配
python -m uiautomator2 init  --serial 127.0.0.1:21523   -- 模拟器的U2更新   u2更新后需要执行这个命令，每个模拟器都要