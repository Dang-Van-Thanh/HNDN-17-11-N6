from odoo import models, fields, api, exceptions
from datetime import datetime

class DatPhong(models.Model):
    _name = "dat_phong"
    _description = "Đăng ký mượn phòng"

    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng họp", required=True)
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn", required=True)  
    thoi_gian_muon_du_kien = fields.Datetime(string="Thời gian mượn dự kiến", required=True)
    thoi_gian_muon_thuc_te = fields.Datetime(string="Thời gian mượn thực tế")
    thoi_gian_tra_du_kien = fields.Datetime(string="Thời gian trả dự kiến", required=True)
    thoi_gian_tra_thuc_te = fields.Datetime(string="Thời gian trả thực tế")

    trang_thai = fields.Selection([
        ("chờ_duyệt", "Chờ duyệt"),
        ("đã_duyệt", "Đã duyệt"),
        ("đang_sử_dụng", "Đang sử dụng"),
        ("đã_hủy", "Đã hủy"),
        ("đã_trả", "Đã trả")
    ], string="Trạng thái", default="chờ_duyệt")

    lich_su_ids = fields.One2many("lich_su_thay_doi", "dat_phong_id", string="Lịch sử mượn trả")
    chi_tiet_su_dung_ids = fields.One2many("dat_phong", "phong_id", string="Chi Tiết Sử Dụng", domain=[("trang_thai", "in", ["đang_sử_dụng", "đã_trả"])])
    def xac_nhan_duyet_phong(self):
        """ Xác nhận duyệt phòng và tự động hủy các yêu cầu bị trùng thời gian (cùng phòng hoặc khác phòng) """
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể duyệt yêu cầu có trạng thái 'Chờ duyệt'.")
            
            # Duyệt yêu cầu hiện tại
            record.write({"trang_thai": "đã_duyệt"})
            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

            # Hủy các yêu cầu cùng phòng có thời gian trùng lặp
            cung_phong_trung_thoi_gian = [
                ('phong_id', '=', record.phong_id.id),
                ('id', '!=', record.id),
                ('trang_thai', '=', 'chờ_duyệt'),
                ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
            ]
            xu_li_cung_phong_trung_thoi_gian = self.search(cung_phong_trung_thoi_gian)
            for other in xu_li_cung_phong_trung_thoi_gian:
                other.write({"trang_thai": "đã_hủy"})
                self.env["dat_phong"].lich_su(other)

            # Hủy các yêu cầu khác phòng nhưng của cùng một người mượn nếu bị trùng thời gian
            khac_phong_trung_thoi_gian = [
                ('nguoi_muon_id', '=', record.nguoi_muon_id.id),
                ('id', '!=', record.id),
                ('trang_thai', '=', 'chờ_duyệt'),
                ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
            ]
            xu_li_khac_phong_trung_thoi_gian = self.search(khac_phong_trung_thoi_gian)
            for other in xu_li_khac_phong_trung_thoi_gian:
                other.write({"trang_thai": "đã_hủy"})
                self.env["dat_phong"].lich_su(other)

    def huy_muon_phong(self):
        """ Hủy đăng ký mượn phòng """
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Chờ duyệt'.")
            record.write({"trang_thai": "đã_hủy"})
            self.env["dat_phong"].lich_su(record)

    def huy_da_duyet(self):
        """ Hủy yêu cầu đã duyệt """
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Đã duyệt'.")
            
            record.write({"trang_thai": "đã_hủy"})
            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

    def bat_dau_su_dung(self):
        """ Bắt đầu sử dụng phòng - Cập nhật thời gian mượn thực tế """
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể bắt đầu sử dụng phòng có trạng thái 'Đã duyệt'.")

            # Kiểm tra nếu đã có người đang sử dụng phòng này
            kiem_tra_phong = self.env["dat_phong"].search([
                ("phong_id", "=", record.phong_id.id),
                ("trang_thai", "=", "đang_sử_dụng"),
                ("id", "!=", record.id)
            ])

            if kiem_tra_phong:
                raise exceptions.UserError(f"Phòng {record.phong_id.name} hiện đang được sử dụng. Vui lòng chờ đến khi phòng trống.")

            # Nếu không có ai đang sử dụng, cho phép bắt đầu
            record.write({
                "trang_thai": "đang_sử_dụng",
                "thoi_gian_muon_thuc_te": datetime.now()
            })
            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })


    def tra_phong(self):
        """ Trả phòng - Cập nhật thời gian trả thực tế và đảm bảo thời gian mượn thực tế có giá trị """
        for record in self:
            if record.trang_thai != "đang_sử_dụng":
                raise exceptions.UserError("Chỉ có thể trả phòng đang ở trạng thái 'Đang sử dụng'.")
            current_time = datetime.now()
            record.write({
                "trang_thai": "đã_trả",
                "thoi_gian_tra_thuc_te": current_time,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te or current_time
            })

            # Lưu vào lịch sử sử dụng tài sản
            tai_san = record.phong_id.tai_san_id
            if tai_san:
                self.env["lich_su_su_dung"].create({
                    "ngay_muon": record.thoi_gian_muon_thuc_te,
                    "ngay_tra": record.thoi_gian_tra_thuc_te,
                    "nhan_vien_id": record.nguoi_muon_id.id,
                    "tai_san_id": tai_san.id,
                    "ghi_chu": f"Mượn phòng {record.phong_id.name}"
                })

            self.env["lich_su_thay_doi"].create({
                "dat_phong_id": record.id,
                "nguoi_muon_id": record.nguoi_muon_id.id,
                "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
                "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
                "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
                "trang_thai": record.trang_thai
            })

    @api.constrains('phong_id', 'thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien')
    def _check_trung_gio_phong(self):
        for record in self:
            if record.phong_id and record.thoi_gian_muon_du_kien and record.thoi_gian_tra_du_kien:
                trung_lap = self.search([
                    ('phong_id', '=', record.phong_id.id),
                    ('id', '!=', record.id),
                    ('trang_thai', '=', 'chờ_duyệt'),
                    ('thoi_gian_muon_du_kien', '<', record.thoi_gian_tra_du_kien),
                    ('thoi_gian_tra_du_kien', '>', record.thoi_gian_muon_du_kien)
                ])
                if trung_lap:
                    raise exceptions.ValidationError(f"Phòng {record.phong_id.name} đã có yêu cầu đặt vào thời gian này. Vui lòng chọn thời gian khác.")
