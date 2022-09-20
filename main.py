import requests, re, json, copy

from constant import GET_API, LOGIN_API, INFO, REPORT_API, USERS, SENDKEY


def ncov_report(username, password,useold):
    session = requests.Session()
    # 尝试访问打卡页
    login_page = session.get(GET_API)
    # 自动跳转至登录页
    # 登录数据
    submit = "登录"
    # submit = re.findall('(<input.*?name="submit".*value=")(.+)(")',login_page.text)[0][1]
    type = "username_password"
    execution = re.findall('(<input\s*name="execution".*?value=")(.+?)(")', login_page.text)[0][1]
    evenId = re.findall('(<input.*?name="_eventId".*value=")(.+)(")', login_page.text)[0][1]
    # 登录
    login_res = session.post(
        LOGIN_API,
        data={
            'username': username,
            'password': password,
            'submit': submit,
            'type': type,
            'execution': execution,
            '_eventId': evenId
        },
        allow_redirects= True
    )
    # 查看是否正确跳转至打卡页
    if login_res.status_code != 200:
        raise RuntimeError('打卡页面获取失败')

    post_data = json.loads(copy.deepcopy(INFO).replace("\n", "").replace(" ", ""))
    # 从html中抽取昨日数据
    try:
        old_data = json.loads('{' + re.findall(r'(?<=oldInfo: {).+(?=})', login_res.text)[0] + '}')
    except:
        print('获取昨日数据失败，将使用固定打卡数据')
        old_data = {}

    # 如使用
    if old_data and useold:
        try:
            for k, v in old_data.items():
                if k in post_data:
                    post_data[k] = v
            geo = json.loads(old_data['geo_api_info'])

            province = geo['addressComponent']['province']
            city = geo['addressComponent']['city']
            if geo['addressComponent']['city'].strip() == "" and len(re.findall(r'北京市|上海市|重庆市|天津市', province)) != 0:
                city = geo['addressComponent']['province']
            area = province + " " + city + " " + geo['addressComponent']['district']
            address = geo['formattedAddress']

            post_data['province'] = province
            post_data['city'] = city
            post_data['area'] = area
            post_data['address'] = address

            # 强行覆盖一些字段
            post_data['ismoved'] = 0  # 是否移动了位置？否
            post_data['bztcyy'] = ''  # 不在同城原因？空
            post_data['sfsfbh'] = 0  # 是否省份不合？否
        except:
            print("加载昨日数据错误，采用固定数据")
            post_data = json.loads(copy.deepcopy(INFO).replace("\n", "").replace(" ", ""))

    report_res = session.post(
        REPORT_API,
        data=post_data
    )
    if report_res.status_code != 200:
        raise RuntimeError('report_res 状态码不是 200')
    return post_data, report_res.text


def server_push(send_key: str, title: str, msg: str):
    server_push_url = "https://sctapi.ftqq.com/{}.send".format(send_key)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    body = {
        'title': title,
        'desp': msg
    }
    return requests.post(url=server_push_url, headers=headers, data=body)

# markdown表格
table = ['| name | msg | address |', '|  :----:  | :----:  | :----:  |']
# 方糖通知标题
title = '《每日填报》{success}/{total}填报成功!'
# 总打卡用户数
total = len(USERS)
# 打卡成功人数
success = 0
for user in USERS:
    username, password, name, useold = user
    try:
        data, res = ncov_report(username = username, password = password, useold = (useold == 0))
    except Exception as e:
        data, res = {}, str(e)
    else:
        success += 1
    msg = '| ' + name + ' | ' + res + ' | ' + data.setdefault('address','未知地址') + ' | '
    table.append(msg)
post_msg = '\n'.join(table)
server_push(SENDKEY,title.format(success = success,total = total),post_msg)
