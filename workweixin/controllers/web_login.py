# -*- coding: utf-8 -*-

import json
import logging

import requests

import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request
from odoo.tools import config

_logger = logging.getLogger(__name__)



class WorkWeiXinController(http.Controller):

	@http.route('/workweixin/web/get_config', type='http', auth='public', csrf=False)
	def get_onfig(self, **kw):
		fields ={'corpid', 'agentid', 'redirect_uri'}
		workweixin = request.env['workweixin.workweixin'].sudo().search_read([], fields=fields, limit=1)
		if workweixin:
			return json.dumps(workweixin[0])
		return ""

	@http.route('/workweixin/web/login', type='http', auth="none")
	def web_login(self, **kw):
		code = kw.get('code')
		appid = kw.get('appid')

		# 消费用户code ,用户校验
		login, uid = self.getLoginBycode(code, appid)
		if login:
			# 创建系统session环境
			self.workweixin_authenticate(request.session.db, login, uid)
			return request.redirect('/web')
		return request.redirect('/web/login')

	def workweixin_authenticate(self, db, login,uid):
		"""
		Authenticate the current user with the given db, login and
		password. If successful, store the authentication parameters in the
		current session and request, unless multi-factor-authentication
		is activated. In that case, that last part will be done by
		:ref:`finalize`.
		"""
		request.session.pre_uid = uid
		request.session.rotate = True
		request.session.db = db
		request.session.login = login
		request.disable_db = False
		user = request.env(user=uid)['res.users'].browse(uid)
		if not user._mfa_url():
			request.session.finalize()

		return uid

	def getLoginBycode(self, code, appid):
		"""
		消费用户code
		"""
		workweixin = request.env['workweixin.workweixin'].sudo().search([("corpid", "=", appid)], limit=1)
		res={}
		if workweixin:
			try:
				# 优先从数据库中获取
				access_token = json.loads(workweixin.access_token)
				access_token = access_token.get("app_token", '')
				if access_token:
					api_url = "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token=" + access_token + "&code=" + code
					res = requests.get(api_url)
					res = json.loads(res.text)
					if res['errcode'] == 0:
						login = res['UserId']
				#token 没有 或 失效时 重新获取token 然后重试
				if not access_token or not res or (not (res['errcode'] == 0 and res['UserId'])):
					access_token = workweixin.get_token(workweixin.corpid, workweixin.secret)
					api_url = "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token=" + access_token + "&code=" + code
					res = requests.get(api_url)
					res = json.loads(res.text)
					login = res['UserId']
					# 将最新的access_token更新到数据库, 并将通讯录token分区到“app_token”中，后面再次拿token的时候通过key “app_token”获取通讯录token
					workweixin_access_token = json.loads(workweixin.access_token)
					workweixin_access_token['app_token'] = access_token
					workweixin.write({"access_token": json.dumps(workweixin_access_token)})
			except Exception:
				raise ValidationError("oauth login  fail")
			if login != '':
				# 校验用户是否存在
				res_user = request.env['res.users'].search([("login", "=", login)], limit=1)
				if res_user:
					return login, res_user.id
			raise ValidationError("oauth login  fail")