from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(string='Gemini API Key', config_parameter='quan_li_phong_hop.gemini_api_key')
