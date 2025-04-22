import time
import csv
import os
import pickle
from datetime import datetime
import requests
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import AlertExistsError
from lxml import etree

# 定义保存路径
SAVE_DIR = r"D:\港科广\自学\Ai\gameAI\code\crap\csv_files"
# 定义进度文件路径
PROGRESS_FILE = r"D:\港科广\自学\Ai\gameAI\code\crap\progress\progress.pkl"
PROGRESS_DIR = os.path.dirname(PROGRESS_FILE)

# 确保目录存在
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
if not os.path.exists(PROGRESS_DIR):
    os.makedirs(PROGRESS_DIR)

def handle_alerts(page):
    """处理页面上的提示框"""
    try:
        # 检查是否存在提示框
        if page.alerts():
            # 获取提示框文本
            alert_text = page.get_alert_text()
            print(f"检测到提示框: '{alert_text}'")
            # 接受提示框
            page.accept_alert()
            print("已接受提示框")
        return True
    except Exception as e:
        print(f"处理提示框时出错: {e}")
        return False

def ti(ai):
    """将时间戳转换为格式化的日期时间字符串"""
    from datetime import datetime
    timestamp = ai
    # 将时间戳转换为 datetime 对象
    dt_object = datetime.fromtimestamp(timestamp)
    # 格式化输出日期时间
    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    return str(formatted_time)

def save_progress(processed_users, current_index):
    """保存爬取进度"""
    progress_data = {
        'processed_users': processed_users,
        'current_index': current_index,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 先保存到临时文件再重命名，防止意外中断导致的文件损坏
    temp_file = PROGRESS_FILE + ".tmp"
    try:
        with open(temp_file, 'wb') as f:
            pickle.dump(progress_data, f)
        
        # 如果存在，先备份旧的进度文件
        if os.path.exists(PROGRESS_FILE):
            backup_file = f"{PROGRESS_FILE}.bak"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(PROGRESS_FILE, backup_file)
        
        # 重命名临时文件为正式文件
        os.rename(temp_file, PROGRESS_FILE)
        print(f"进度已保存: 已处理 {current_index} 个用户")
        return True
    except Exception as e:
        print(f"保存进度失败: {e}")
        return False

def load_progress():
    """加载之前的爬取进度"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'rb') as f:
                progress_data = pickle.load(f)
            print(f"找到历史进度 ({progress_data.get('timestamp', '未知时间')})")
            print(f"已处理 {progress_data['current_index']} 个用户")
            return progress_data
        except Exception as e:
            print(f"加载进度失败: {e}")
            # 尝试从备份恢复
            backup_file = f"{PROGRESS_FILE}.bak"
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'rb') as f:
                        progress_data = pickle.load(f)
                    print(f"从备份恢复进度 ({progress_data.get('timestamp', '未知时间')})")
                    return progress_data
                except:
                    print("备份进度也无法加载")
    
    return {'processed_users': [], 'current_index': 0}

def is_user_processed(username):
    """检查用户是否已经处理过"""
    # 检查CSV文件是否存在且有内容
    csv_path = os.path.join(SAVE_DIR, f'{username}.csv')
    return os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

def create_browser():
    """创建浏览器实例"""
    try:
        # 创建浏览器选项
        options = ChromiumOptions()
        # 设置页面加载策略
        options.page_load_strategy = 'eager'
        # 禁用自动化控制特性，避免被网站检测为爬虫
        options.set_argument('--disable-blink-features=AutomationControlled')
        # 禁用网页通知
        options.set_argument('--disable-notifications')
        # 启用JavaScript
        options.set_argument('--enable-javascript')
        # 禁用扩展
        options.set_argument('--disable-extensions')
        # 设置窗口大小（使用命令行参数）
        options.set_argument('--window-size=1280,800')

        # 创建浏览器
        page = ChromiumPage(options)
        return page
    except Exception as e:
        print(f"创建浏览器实例时出错: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def cctv2(gjc):
    """爬取单个用户的数据"""
    print(f"开始爬取用户 {gjc} 的数据...")
    
    # 检查是否已爬取过该用户
    csv_path = os.path.join(SAVE_DIR, f'{gjc}.csv')
    if is_user_processed(gjc):
        print(f"用户 {gjc} 已爬取过，跳过")
        return True
    
    try:
        # 创建一个 ChromiumPage 对象
        page = create_browser()
        if not page:
            print("创建浏览器失败，无法继续")
            return False
        
        # 监听API响应
        page.listen.start('https://nodocchi.moe/api/listuser.php?')
        
        # 访问用户页面
        print(f"访问用户页面: https://nodocchi.moe/tenhoulog/index.html#!&name={gjc}")
        page.get(f'https://nodocchi.moe/tenhoulog/index.html#!&name={gjc}')
        
        # 处理可能的提示框
        handle_alerts(page)
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(3)
        
        # 再次处理可能的提示框
        handle_alerts(page)
        
        # 获取API响应
        print("等待API响应...")
        packet = page.listen.wait(timeout=30)
        if not packet:
            print(f"未捕获到用户 {gjc} 的API响应")
            return False
        
        # 获取响应内容
        response = packet.response.body
        
        # 检查响应格式
        if not isinstance(response, dict) or 'list' not in response:
            print(f"响应格式不正确: {type(response)}")
            return False
        
        # 处理数据
        record_count = 0
        for i in response['list']:
            dic = {}
            dic['顺位'] = str(i.get('playernum', '')) + '位'
            
            # 使用get方法安全获取字段，避免异常
            dic['用时'] = i.get('during', '')
            dic['开始时间'] = ti(i.get('starttime', 0))
            dic['牌普'] = i.get('url', '')
            dic['一号玩家'] = i.get('player1', '')
            dic['一位得点'] = i.get('player1ptr', '')
            dic['二号玩家'] = i.get('player2', '')
            dic['二位得点'] = i.get('player2ptr', '')
            dic['三号玩家'] = i.get('player3', '')
            dic['三位得点'] = i.get('player3ptr', '')
            dic['四号玩家'] = i.get('player4', '')
            dic['四位得点'] = i.get('player4ptr', '')
            
            lst = []
            print(dic)
            lst.append(dic)
            
            # 保存到指定目录下的CSV文件
            with open(csv_path, 'a+', encoding='utf-8-sig', newline='') as f:
                write = csv.DictWriter(f, fieldnames=dic.keys())
                
                # 检查是否需要写入表头
                f.seek(0)
                if len(f.read()) == 0:
                    write.writeheader()
                
                # 定位到文件末尾
                f.seek(0, 2)
                write.writerows(lst)
            
            record_count += 1
        
        print(f"用户 {gjc} 数据爬取完成，共 {record_count} 条记录")
        return True
        
    except AlertExistsError as e:
        print(f"存在未处理的提示框: {e}")
        try:
            if 'page' in locals():
                # 尝试处理提示框
                handle_alerts(page)
        except:
            pass
        return False
    except Exception as e:
        print(f"爬取用户 {gjc} 时出错: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
        # 确保关闭浏览器
        try:
            if 'page' in locals() and page:
                page.quit()
                print("浏览器已关闭")
        except:
            pass

def cctv1(url):
    """从排行榜页面获取用户列表并爬取数据"""
    print(f"开始从 {url} 爬取用户列表...")
    
    # 加载之前的进度
    progress_data = load_progress()
    processed_users = progress_data.get('processed_users', [])
    current_index = progress_data.get('current_index', 0)
    
    # 询问是否继续之前的进度
    if current_index > 0 and processed_users:
        choice = input(f"是否继续上次进度？已爬取 {current_index} 个用户 (y/n): ").strip().lower()
        if choice != 'y':
            # 用户选择重新开始
            processed_users = []
            current_index = 0
    
    # 如果没有历史数据，重新爬取用户列表
    if not processed_users:
        try:
            # 创建一个 ChromiumPage 对象
            page = create_browser()
            if not page:
                print("创建浏览器失败，无法继续")
                return
            
            try:
                # 访问页面
                print(f"访问页面: {url}")
                page.get(url)
                
                # 处理可能的提示框
                handle_alerts(page)
                
                # 等待页面加载
                print("等待页面加载...")
                time.sleep(3)
                
                # 再次处理可能的提示框
                handle_alerts(page)
                
                # 点击必要的按钮加载内容
                try:
                    # 尝试点击4人场按钮
                    player4_btn = page.ele('.graderank_btn_playernum_4')
                    if player4_btn:
                        player4_btn.click()
                        print("已点击4人场按钮")
                        time.sleep(1)
                        handle_alerts(page)
                    
                    # 尝试点击排序按钮
                    order_btn = page.ele('.graderank_btn_orderby_0')
                    if order_btn:
                        order_btn.click()
                        print("已点击排序按钮")
                        time.sleep(1)
                        handle_alerts(page)
                except Exception as e:
                    print(f"点击按钮时出错: {e}")
                
                # 获取页面HTML
                html = page.html
                
                # 解析HTML
                ele = etree.HTML(html)
                
                # 获取所有玩家元素
                user_elements = ele.xpath('//div[@class="graderank_playernum_4 graderank_orderby_0 graderank_rg_0"]/table/tbody/tr')
                
                if not user_elements:
                    print("未找到玩家数据，尝试其他XPath...")
                    user_elements = ele.xpath('//table/tbody/tr')
                
                # 提取用户名和链接
                users_to_process = []
                for i in user_elements:
                    try:
                        username = i.xpath('.//td[@class="graderank_table_col_username nostretch"]/a/text()')[0]
                        user_url = i.xpath('.//td[@class="graderank_table_col_username nostretch"]/a/@href')[0]
                        users_to_process.append((username, user_url))
                    except:
                        # 如果提取失败，尝试其他XPath
                        try:
                            cells = i.xpath('.//td')
                            if cells and len(cells) > 1:
                                username_cell = cells[1]  # 通常第二列是用户名
                                a_elements = username_cell.xpath('.//a')
                                if a_elements:
                                    username = a_elements[0].text
                                    user_url = a_elements[0].get('href', '')
                                    if username:
                                        users_to_process.append((username, user_url))
                        except:
                            continue
                
                print(f"共找到 {len(users_to_process)} 个用户")
                
                # 如果找不到用户，使用默认列表
                if not users_to_process:
                    users_to_process = [
                        ("ASAPIN", ""),
                        ("trars", ""),
                        ("Ⅸ-CactuaR-Ⅸ", ""),
                        ("wassermann", ""),
                        ("ひとくちぷっちょ", "")
                    ]
                    print(f"未找到用户，使用默认列表，共 {len(users_to_process)} 个用户")
                
                # 更新进度信息
                processed_users = users_to_process
                current_index = 0
                save_progress(processed_users, current_index)
                
            except AlertExistsError as e:
                print(f"存在未处理的提示框: {e}")
                handle_alerts(page)
                print("使用默认用户列表")
                users_to_process = [
                    ("ASAPIN", ""),
                    ("trars", ""),
                    ("Ⅸ-CactuaR-Ⅸ", ""),
                    ("wassermann", ""),
                    ("ひとくちぷっちょ", "")
                ]
                processed_users = users_to_process
                current_index = 0
                save_progress(processed_users, current_index)
            
            finally:
                # 关闭浏览器
                if page:
                    page.quit()
                    print("浏览器已关闭")
            
        except Exception as e:
            print(f"获取用户列表时出错: {e}")
            import traceback
            print(traceback.format_exc())
            
            # 使用默认列表
            print("使用默认用户列表")
            users_to_process = [
                ("ASAPIN", ""),
                ("trars", ""),
                ("Ⅸ-CactuaR-Ⅸ", ""),
                ("wassermann", ""),
                ("ひとくちぷっちょ", "")
            ]
            processed_users = users_to_process
            current_index = 0
            save_progress(processed_users, current_index)
    
    # 开始爬取用户数据
    total_users = len(processed_users)
    print(f"开始爬取 {total_users} 个用户的数据...")
    
    if total_users == 0:
        print("没有用户需要爬取，程序退出")
        return
    
    success_count = 0
    fail_count = 0
    
    try:
        # 从当前索引开始爬取
        for i in range(current_index, total_users):
            username, _ = processed_users[i]
            
            print(f"\n处理 {i+1}/{total_users} 用户: {username}")
            
            # 检查是否已经爬取过
            if is_user_processed(username):
                print(f"用户 {username} 已爬取过，跳过")
                current_index = i + 1
                save_progress(processed_users, current_index)
                continue
            
            # 爬取用户数据
            success = cctv2(username)
            
            # 更新统计和进度
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            current_index = i + 1
            save_progress(processed_users, current_index)
            
            # 显示进度
            progress = (current_index / total_users) * 100
            print(f"总进度: {progress:.2f}% ({current_index}/{total_users})")
            print(f"成功: {success_count}, 失败: {fail_count}")
            
            # 等待一段时间，避免请求过快
            if i < total_users - 1:  # 如果不是最后一个用户
                wait_time = 2  # 可以根据需要调整等待时间
                print(f"等待 {wait_time} 秒...")
                time.sleep(wait_time)
                
    except KeyboardInterrupt:
        # 处理用户中断
        print("\n用户中断程序，保存当前进度...")
        save_progress(processed_users, current_index)
        print(f"进度已保存，下次运行将从第 {current_index+1} 个用户继续")
    except Exception as e:
        print(f"爬取过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
        # 保存当前进度
        save_progress(processed_users, current_index)
    
    print("\n爬取完成！")
    print(f"成功: {success_count}, 失败: {fail_count}")

# 主程序入口
if __name__ == "__main__":
    print("=== 天凤牌谱爬取工具 ===")
    
    # 询问用户选择操作模式
    print("\n请选择操作模式:")
    print("1. 从排行榜页面爬取多个用户")
    print("2. 爬取单个用户数据")
    print("3. 退出")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == '1':
        # 从排行榜爬取
        url = input("请输入排行榜URL (直接回车使用默认URL): ").strip()
        if not url:
            url = 'https://nodocchi.moe/tenhoulog/graderank.html#!&playernum=4&orderby=0&rg=0'
            print(f"使用默认URL: {url}")
        
        cctv1(url)
        
    elif choice == '2':
        # 爬取单个用户
        username = input("请输入用户名: ").strip()
        if username:
            cctv2(username)
        else:
            print("用户名不能为空")
            
    elif choice == '3':
        print("程序已退出")
        
    else:
        print("无效选择，程序已退出")