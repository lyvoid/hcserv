# -*-coding:utf-8-*-

import re
from datetime import datetime, timedelta
from flask import jsonify, request
from serv.serv_base import app
from dao.models import UserInfo
from utils.tools import md5


game_id_pattern = re.compile(r'^\d{7}$')


@app.route('/hcserv/verify')
def verify():
    # 获取参数
    game_id = request.args.get('game_id')
    request_secret = request.args.get('secret')
    request_time = request.args.get('time')
    if game_id is None \
            or request_secret is None \
            or request_time is None \
            or game_id_pattern.match(game_id) is None:
        return jsonify({'error': 'not enough param'})

    # 验证请求有效性
    now = datetime.now()
    now_timestamp = int(now.timestamp())
    request_timestamp = int(request_time)
    time_delta = now_timestamp - request_timestamp
    if time_delta < -120 or time_delta > 120:
        # 如果请求时间与当前时间差2分钟，则该请求已过期
        return jsonify({'error': 'request is expired'})
    if request_secret != md5('%s%s' % (game_id[:5], request_time)):
        # 如果加密的md5对不上，说明请求被篡改
        return jsonify({'error': 'error'})

    # 用户信息验证
    user = UserInfo()
    user.game_id = int(game_id)
    is_user_exist = user.load()

    if is_user_exist:
        is_expire = now_timestamp <= user.expire_time
    else:
        # 如果用户不存在，注册用户，并免费赠送7天时间
        day_expire = now.date() + timedelta(days=8)
        user.expire_time = int(datetime(
            day_expire.year,
            day_expire.month,
            day_expire.day,
            0,
            0
        ).timestamp())
        user.register_time = now_timestamp
        is_expire = True

    user.last_login_time = now_timestamp
    user.login_times = 1 if user.login_times is None else user.login_times + 1

    user.commit()

    expire_days = (datetime.fromtimestamp(
        user.expire_time
    ) - now).days

    secret_time = str(now_timestamp)
    return jsonify({
        "game_id": game_id,
        "is_expire": is_expire,
        "expire_days": expire_days,
        "is_new": not is_user_exist,
        "time": secret_time,
        "secret": md5('%s%s%s' % (md5(secret_time), md5(game_id), md5(str(is_expire).lower())))
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0')
