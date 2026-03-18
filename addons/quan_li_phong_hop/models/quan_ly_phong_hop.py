from odoo import models, fields, api

class QuanLyPhongHop(models.Model):
    _name = "quan_ly_phong_hop"
    _description = "Quản lý phòng họp, hội trường"

    name = fields.Char(string="Tên phòng họp", required=True)
    loai_phong = fields.Selection([
        ("Phòng_họp", "Phòng họp"),
        ("Hội_trường", "Hội trường"),
    ], string="Loại phòng", required=True, default="Phòng_họp")
    suc_chua = fields.Integer(string="Sức chứa")

    tai_san_id = fields.Many2one('tai_san', string="Tài sản tương ứng", readonly=True)

    trang_thai = fields.Selection([
        ("Trống", "Trống"),
        ("Đã_mượn", "Đã mượn"),
        ("Đang_sử_dụng", "Đang sử dụng"),
    ], string="Trạng thái", compute="_compute_trang_thai", store=True)

    dat_phong_ids = fields.One2many("dat_phong", "phong_id", string="Lịch sử mượn phòng")
    # Chỉ hiển thị các trạng thái "Đã duyệt" và "Đang sử dụng"
    lich_dat_phong_ids = fields.One2many(
        "dat_phong", "phong_id",
        string="Lịch đặt phòng",
        domain=[("trang_thai", "in", ["đã_duyệt", "đang_sử_dụng"])]
    )

    # Lịch sử mượn trả (Chỉ hiển thị các trạng thái "Đã trả")
    lich_su_thay_doi_ids = fields.One2many(
        "dat_phong", "phong_id",
        string="Lịch sử mượn trả",
        domain=[("trang_thai", "=", "đã_trả")]
    )

    @api.depends("dat_phong_ids.trang_thai")
    def _compute_trang_thai(self):
        for record in self:
            trang_thai_dat_phong = record.dat_phong_ids.filtered(lambda r: r.trang_thai in ["đã_duyệt", "đang_sử_dụng"])
            trang_thai_dang_su_dung = record.dat_phong_ids.filtered(lambda r: r.trang_thai == "đang_sử_dụng")
            trang_thai_da_huy_da_tra = record.dat_phong_ids.filtered(lambda r: r.trang_thai in ["đã_hủy", "đã_trả"])

            if trang_thai_dang_su_dung:
                record.trang_thai = "Đang_sử_dụng"
            elif trang_thai_dat_phong:
                record.trang_thai = "Đã_mượn"
            elif trang_thai_da_huy_da_tra:
                record.trang_thai = "Trống"
            else:
                record.trang_thai = "Trống"
            
            # Đồng bộ trạng thái với tài sản
            if record.tai_san_id:
                if record.trang_thai == "Đang_sử_dụng":
                    record.tai_san_id.trang_thai = "Muon"
                elif record.trang_thai == "Đã_mượn":
                    record.tai_san_id.trang_thai = "Muon"
                else:
                    record.tai_san_id.trang_thai = "CatGiu"

    @api.model
    def create(self, vals):
        # Tạo tài sản tương ứng
        loai_phong = vals.get('loai_phong', 'Phòng_họp')
        ten_loai = "Phòng họp" if loai_phong == "Phòng_họp" else "Hội trường"
        loai_ts = self.env['loai_tai_san'].search([('ten_loai_tai_san', '=', ten_loai)], limit=1)
        if not loai_ts:
            loai_ts = self.env['loai_tai_san'].create({
                'ma_loai_tai_san': ten_loai.replace(' ', '_'),
                'ten_loai_tai_san': ten_loai,
            })
        tai_san_vals = {
            'ma_tai_san': vals.get('name', 'New'),
            'so_serial': vals.get('name', 'New'),
            'ten_tai_san': vals['name'],
            'loai_tai_san_id': loai_ts.id,
        }
        tai_san = self.env['tai_san'].create(tai_san_vals)
        vals['tai_san_id'] = tai_san.id
        return super(QuanLyPhongHop, self).create(vals)
