# -*- coding: utf-8 -*-

import json

import requests

from odoo import models, fields,api
from odoo.http import request
from odoo.exceptions import AccessDenied,Warning

# 企业微信基础url
base_url = "https://qyapi.weixin.qq.com/cgi-bin/"

#token_api
gettoken = "gettoken?corpid={}&corpsecret={}"

#token_api 	部门id。获取指定部门及其下的子部门（以及子部门的子部门等等，递归）。 如果不填，默认获取全量组织架构
department_list = "department/list?access_token={}&id={}"

#获取所有成员
simplel = "/user/simplelist?department_id=1&fetch_child=1&access_token={}"

class WorkWeiXin(models.Model):
    _name = 'workweixin.workweixin'
    _description = 'workweixin.workweixin'
    # 自建应用相关配置参数
    name = fields.Char(string='应用名称', required=True)
    agentid = fields.Char(string='应用agentid', required=True)
    redirect_uri = fields.Char(string='应用跳转url', required=True)
    secret = fields.Char(string='应用密钥', required=True)
    # 企业相关配置参数  appid
    corpid = fields.Char(string='企业Id', required=True)
    corpsecret = fields.Char(string='通讯录密钥', required=True)
    access_token = fields.Char(string='token')

    _sql_constraints = [('check_corpid_uniq', 'UNIQUE(corpid)', '企业Id唯一')]

    @api.model
    def create(self, vals_list):
        # 获取token
        access_token = self.get_token(vals_list['corpid'], vals_list['corpsecret'])

        # 同时保存通讯录token
        vals_list['access_token'] = json.dumps({"corp_token": access_token})

        res = super(WorkWeiXin, self).create(vals_list)

        # 创建配置的同时 同步企业微信的用户
        res.syn_users()

        return res

    # 获取access_token  默认有效期2小时
    def get_token(self, corpid, secret):
        try:
            api_url = base_url + gettoken.format(corpid, secret)
            res = requests.get(api_url)
            res = json.loads(res.text)
            if res['errcode'] == 0 and res['access_token']:
                return res['access_token']
            else:
                raise AccessDenied(res['errmsg'])
        except Exception:
            raise AccessDenied("获取token失败！")

    # 用户同步
    def syn_users(self):
        access_token_json = json.loads(self.access_token)
        try:
            api_url = base_url + simplel.format(access_token_json.get('corp_token', ''))
            res = requests.get(api_url)
            res = json.loads(res.text)
            # token过期后重写获取token
            if not (res['errcode'] == 0 and res['userlist']):
                access_token = self.get_token(self.corpid, self.corpsecret)
                api_url = base_url + simplel.format(access_token)
                res = requests.get(api_url)
                res = json.loads(res.text)
                #将最新的access_token更新到数据库, 并将通讯录token分区到“corp_token”中，后面再次拿token的时候通过key “corp_token”获取通讯录token
                self.write({"access_token": json.dumps({"corp_token": access_token})})
        except Exception:
            raise AccessDenied("同步用户失败！")
        # 获取到用户数据后同步到res_user
        if res['errcode'] == 0 and res['userlist']:
            res_users_create = []
            for val in res['userlist']:
                res_user_dict = {}
                res_user_dict['name'] = val['name']
                res_user_dict['login'] = val['userid']
                res_user = request.env['res.users'].sudo().search([('login', '=', val['userid'])], limit=1)
                if res_user:
                    res_user.write(res_user_dict)
                else:
                    res_users_create.append(res_user_dict)
            if res_users_create:
                request.env['res.users'].sudo().create(res_users_create)