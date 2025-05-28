import cv2
import numpy as np
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageGrab, ImageDraw
import os
from datetime import datetime
import math

class EnhancedImageMeasurementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高级图片测量工具(ganta_dg增强版)")
        self.root.geometry("1200x900")
        
        # 初始化变量
        self.image_paths = []
        self.current_image_index = -1
        self.scale_factor = 1.0
        self.drawing_mode = None
        self.start_point = None
        self.current_line = None
        self.reference_line = None
        self.measurements = []
        self.continuous_mode = False
        self.original_image = None
        self.display_scale = 1.0
        self.last_scale = 1.0
        self.scale_center = (0, 0)
        
        # 梯形截图相关变量
        self.screenshot_mode = False
        self.screenshot_points = []
        self.screenshot_lines = []
        self.screenshot_preview = None
        
        # 正交参考线相关变量
        self.horizontal_reference_lines = []
        self.vertical_reference_lines = []
        
        # 画框抠图相关变量
        self.crop_mode = False
        self.crop_rect = None
        self.crop_start = None
        
        self.setup_ui()
    
    def setup_ui(self):
        control_frame = Frame(self.root, padx=10, pady=10)
        control_frame.pack(side=TOP, fill=X)
        
        # 图片导航控制
        nav_frame = Frame(control_frame)
        nav_frame.pack(side=LEFT, padx=5)
        
        self.btn_prev = Button(nav_frame, text="上一张", command=self.prev_image, state=DISABLED)
        self.btn_prev.pack(side=LEFT, padx=2)
        self.btn_next = Button(nav_frame, text="下一张", command=self.next_image, state=DISABLED)
        self.btn_next.pack(side=LEFT, padx=2)
        self.image_counter = Label(nav_frame, text="0/0")
        self.image_counter.pack(side=LEFT, padx=5)
        
        self.btn_load = Button(control_frame, text="上传图片", command=self.load_image)
        self.btn_load.pack(side=LEFT, padx=5)
        
        # 添加旋转按钮
        self.btn_rotate = Button(control_frame, text="旋转90度", 
                               command=self.rotate_image,
                               state=DISABLED)
        self.btn_rotate.pack(side=LEFT, padx=5)
        
        Label(control_frame, text="参考长度(cm):").pack(side=LEFT, padx=5)
        self.entry_length = Entry(control_frame, width=10)
        self.entry_length.pack(side=LEFT, padx=5)
        
        self.btn_set_ref = Button(control_frame, text="设置参考线", 
                                command=lambda: self.set_mode('reference'),
                                state=DISABLED)
        self.btn_set_ref.pack(side=LEFT, padx=5)
        
        self.btn_measure = Button(control_frame, text="测量模式", 
                                command=lambda: self.set_mode('measurement'),
                                state=DISABLED)
        self.btn_measure.pack(side=LEFT, padx=5)
        
        self.btn_continuous = Button(control_frame, text="连续测量", 
                                   command=self.toggle_continuous_mode,
                                   state=DISABLED)
        self.btn_continuous.pack(side=LEFT, padx=5)
        
        self.btn_undo = Button(control_frame, text="撤销", 
                             command=self.undo_last_measurement,
                             state=DISABLED)
        self.btn_undo.pack(side=LEFT, padx=5)
        
        self.btn_clear = Button(control_frame, text="清除测量", 
                              command=self.clear_measurements,
                              state=DISABLED)
        self.btn_clear.pack(side=LEFT, padx=5)
        
        # 截图按钮
        self.btn_screenshot = Button(control_frame, text="梯形截图", 
                                   command=self.toggle_screenshot_mode,
                                   state=DISABLED)
        self.btn_screenshot.pack(side=LEFT, padx=5)
        
        # 正交参考线按钮
        self.btn_ortho = Button(control_frame, text="正交参考线", 
                              command=self.add_orthogonal_reference,
                              state=DISABLED)
        self.btn_ortho.pack(side=LEFT, padx=5)
        
        # 画框抠图按钮
        self.btn_crop = Button(control_frame, text="画框抠图", 
                             command=self.toggle_crop_mode,
                             state=DISABLED)
        self.btn_crop.pack(side=LEFT, padx=5)
        
        # 保存按钮
        self.btn_save = Button(control_frame, text="保存图片", 
                             command=self.save_image,
                             state=DISABLED)
        self.btn_save.pack(side=LEFT, padx=5)
        
        # 缩放控制
        Label(control_frame, text="显示缩放:").pack(side=LEFT, padx=5)
        self.scale_var = DoubleVar(value=1.0)
        self.scale_slider = Scale(control_frame, from_=0.1, to=3.0, resolution=0.1, 
                                orient=HORIZONTAL, variable=self.scale_var,
                                command=self.on_scale_change, length=150)
        self.scale_slider.pack(side=LEFT, padx=5)
        self.btn_reset_zoom = Button(control_frame, text="重置缩放", 
                                   command=self.reset_zoom)
        self.btn_reset_zoom.pack(side=LEFT, padx=5)
        
        # 创建带滚动条的画布框架
        self.canvas_frame = Frame(self.root)
        self.canvas_frame.pack(side=TOP, fill=BOTH, expand=True)
        
        # 滚动条
        self.hscroll = Scrollbar(self.canvas_frame, orient=HORIZONTAL)
        self.hscroll.pack(side=BOTTOM, fill=X)
        self.vscroll = Scrollbar(self.canvas_frame)
        self.vscroll.pack(side=RIGHT, fill=Y)
        
        # 创建画布
        self.canvas = Canvas(self.canvas_frame, bg="gray",
                            xscrollcommand=self.hscroll.set,
                            yscrollcommand=self.vscroll.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        # 配置滚动条
        self.hscroll.config(command=self.canvas.xview)
        self.vscroll.config(command=self.canvas.yview)
        
        # 绑定事件
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.end_drawing)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-2>", self.on_middle_button_press)
        self.canvas.bind("<B2-Motion>", self.on_middle_button_drag)

        # 结果区域
        results_frame = Frame(self.root, padx=10, pady=10)
        results_frame.pack(side=BOTTOM, fill=X)
        
        Label(results_frame, text="测量结果", font=("Arial", 12)).pack(anchor=W)
        
        self.total_var = StringVar()
        self.total_var.set("总计: 0.00 cm")
        Label(results_frame, textvariable=self.total_var, font=("Arial", 10, "bold")).pack(anchor=E)
        
        self.results_table = ttk.Treeview(results_frame, columns=("length"), show="headings")
        self.results_table.heading("length", text="长度(cm)")
        self.results_table.column("length", width=200, anchor=CENTER)
        self.results_table.pack(fill=X)
        
        self.status_var = StringVar()
        self.status_var.set("请上传图片并设置参考线")
        status_bar = Label(self.root, textvariable=self.status_var, bd=1, relief=SUNKEN, anchor=W)
        status_bar.pack(side=BOTTOM, fill=X)
    
    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_image_at_index(self.current_image_index)
    
    def next_image(self):
        if self.current_image_index < len(self.image_paths) - 1:
            self.current_image_index += 1
            self.load_image_at_index(self.current_image_index)
    
    def load_image_at_index(self, index):
        if 0 <= index < len(self.image_paths):
            self.image_path = self.image_paths[index]
            try:
                with open(self.image_path, "rb") as f:
                    img_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
                    self.cv_image = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
            except Exception as e:
                self.cv_image = None
                self.status_var.set("读取图片失败")
                return

            if self.cv_image is None:
                self.status_var.set("图片加载失败，请检查路径或文件格式")
                return

            self.cv_image = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)
            self.original_image = self.cv_image.copy()
            
            self.reset_zoom()
            
            self.btn_set_ref.config(state=NORMAL)
            self.btn_measure.config(state=NORMAL)
            self.btn_continuous.config(state=NORMAL)
            self.btn_undo.config(state=NORMAL)
            self.btn_clear.config(state=NORMAL)
            self.btn_screenshot.config(state=NORMAL)
            self.btn_rotate.config(state=NORMAL)
            self.btn_ortho.config(state=NORMAL)
            self.btn_crop.config(state=NORMAL)
            self.btn_save.config(state=NORMAL)
            
            # 更新导航按钮状态
            self.btn_prev.config(state=NORMAL if index > 0 else DISABLED)
            self.btn_next.config(state=NORMAL if index < len(self.image_paths)-1 else DISABLED)
            self.image_counter.config(text=f"{index+1}/{len(self.image_paths)}")
            
            self.status_var.set(f"已加载图片 {index+1}/{len(self.image_paths)}: {os.path.basename(self.image_path)}")
    
    def toggle_crop_mode(self):
        """切换画框抠图模式"""
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            # 进入抠图模式
            self.drawing_mode = None
            self.screenshot_mode = False
            self.btn_crop.config(relief=SUNKEN, bg="lightgreen")
            self.status_var.set("画框抠图模式: 请在图片上拖动绘制矩形框")
        else:
            # 退出抠图模式
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
                self.crop_rect = None
            self.crop_start = None
            self.btn_crop.config(relief=RAISED, bg="SystemButtonFace")
            self.status_var.set("已退出画框抠图模式")
    
    def save_image(self):
        """保存当前图片"""
        if self.original_image is None:
            return
            
        # 获取保存路径
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            initialfile=f"modified_{os.path.basename(self.image_path)}"
        )
        
        if not save_path:
            return
            
        try:
            # 转换回BGR格式保存
            save_image = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(save_path, save_image)
            self.status_var.set(f"图片已保存到: {save_path}")
        except Exception as e:
            self.status_var.set(f"保存图片失败: {str(e)}")
    
    def add_orthogonal_reference(self):
        """添加一条横跨图像宽度的水平参考线，并设置为参考比例尺"""
        if self.original_image is None:
            return

        self.clear_reference_lines()

        h, w = self.original_image.shape[:2]
        x1 = 0
        x2 = w
        y = int(h / 2)

        # 直接保存原始图像坐标（不再乘以display_scale）
        self.reference_line = (x1, y, x2, y)

        # 使用用户输入的参考长度计算比例
        try:
            real_length = float(self.entry_length.get())
            if real_length <= 0:
                raise ValueError
        except ValueError:
            self.status_var.set("请输入有效的参考长度(cm)后再使用该功能")
            return

        pixel_length = (x2 - x1)
        self.scale_factor = real_length / pixel_length
        self.status_var.set(f"已添加参考线并设置比例尺: 1像素 = {self.scale_factor:.6f} 厘米")
        self.update_canvas()



    def clear_reference_lines(self):
        """清除所有参考线"""
        self.horizontal_reference_lines = []
        self.vertical_reference_lines = []
        self.update_canvas()
    
    def rotate_image(self):
        """顺时针旋转图像90度"""
        if self.original_image is None:
            return
            
        try:
            # 使用OpenCV旋转图像90度
            rotated = cv2.rotate(self.original_image, cv2.ROTATE_90_CLOCKWISE)
            
            # 更新图像
            self.original_image = rotated
            self.cv_image = rotated.copy()
            
            # 重置测量数据和参考线
            self.reference_line = None
            self.measurements = []
            self.clear_reference_lines()
            self.update_results_table()
            
            # 保持当前缩放比例
            current_scale = self.display_scale
            self.reset_zoom()
            self.scale_var.set(current_scale)
            self.display_scale = current_scale
            self.update_canvas()
            
            self.status_var.set("图像已顺时针旋转90度")
            
        except Exception as e:
            self.status_var.set(f"旋转失败: {str(e)}")
    
    def toggle_screenshot_mode(self):
        """切换梯形截图模式"""
        self.screenshot_mode = not self.screenshot_mode
        if self.screenshot_mode:
            # 进入截图模式
            self.drawing_mode = None
            self.crop_mode = False
            self.screenshot_points = []
            self.screenshot_lines = []
            self.btn_screenshot.config(relief=SUNKEN, bg="lightgreen")
            self.status_var.set("梯形截图模式: 请依次点击4个点(顺时针或逆时针)")
        else:
            # 退出截图模式
            self.clear_screenshot_preview()
            self.btn_screenshot.config(relief=RAISED, bg="SystemButtonFace")
            self.status_var.set("已退出梯形截图模式")
    
    def clear_screenshot_preview(self):
        """清除截图预览"""
        for line in self.screenshot_lines:
            self.canvas.delete(line)
        self.screenshot_lines = []
        self.screenshot_points = []
        if self.screenshot_preview:
            self.canvas.delete(self.screenshot_preview)
            self.screenshot_preview = None
    
    def add_screenshot_point(self, x, y):
        """添加截图点"""
        if len(self.screenshot_points) >= 4:
            return False
        
        # 转换坐标为画布坐标
        x = self.canvas.canvasx(x)
        y = self.canvas.canvasy(y)
        
        self.screenshot_points.append((x, y))
        
        # 绘制点
        point = self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="green", outline="green")
        self.screenshot_lines.append(point)
        
        # 绘制连线
        if len(self.screenshot_points) > 1:
            prev_x, prev_y = self.screenshot_points[-2]
            line = self.canvas.create_line(prev_x, prev_y, x, y, fill="green", width=2)
            self.screenshot_lines.append(line)
        
        # 如果已经选择了4个点，闭合区域
        if len(self.screenshot_points) == 4:
            first_x, first_y = self.screenshot_points[0]
            line = self.canvas.create_line(x, y, first_x, first_y, fill="green", width=2)
            self.screenshot_lines.append(line)
            
            # 执行截图和变换
            self.process_screenshot()
            return False
        
        return True
    
    def process_screenshot(self):
        """处理梯形截图并拉直为矩形，然后替换当前画布图像"""
        if len(self.screenshot_points) != 4:
            return
        
        try:
            # 获取原始图像
            if self.original_image is None:
                raise ValueError("没有可用的原始图像")
            
            # 检查image_item是否存在
            if not hasattr(self, 'image_item'):
                raise ValueError("图像未正确加载")
            
            # 将截图点转换为原始图像坐标
            original_points = []
            img_coords = self.canvas.coords(self.image_item)
            for x, y in self.screenshot_points:
                # 转换为相对于图像的坐标
                rel_x = (x - img_coords[0]) / self.display_scale
                rel_y = (y - img_coords[1]) / self.display_scale
                
                # 确保坐标在图像范围内
                rel_x = max(0, min(self.original_image.shape[1]-1, rel_x))
                rel_y = max(0, min(self.original_image.shape[0]-1, rel_y))
                original_points.append((rel_x, rel_y))
            
            # 计算输出矩形的宽度和高度
            width = max(
                math.hypot(original_points[1][0]-original_points[0][0], original_points[1][1]-original_points[0][1]),
                math.hypot(original_points[3][0]-original_points[2][0], original_points[3][1]-original_points[2][1])
            )
            height = max(
                math.hypot(original_points[2][0]-original_points[1][0], original_points[2][1]-original_points[1][1]),
                math.hypot(original_points[0][0]-original_points[3][0], original_points[0][1]-original_points[3][1])
            )
            
            # 定义目标矩形
            dst_points = np.array([
                [0, 0],
                [width, 0],
                [width, height],
                [0, height]
            ], dtype=np.float32)
            
            # 转换为numpy数组
            src_points = np.array(original_points, dtype=np.float32)
            
            # 计算透视变换矩阵
            M = cv2.getPerspectiveTransform(src_points, dst_points)
            
            # 应用透视变换
            warped = cv2.warpPerspective(self.original_image, M, (int(width), int(height)))
            
            # 更新当前图像为变换后的图像
            self.original_image = warped
            self.cv_image = warped.copy()
            
            # 重置测量数据
            self.reference_line = None
            self.measurements = []
            self.clear_reference_lines()
            self.update_results_table()
            
            # 更新画布显示
            self.reset_zoom()
            self.status_var.set("梯形区域已拉直并显示在画布上")
            
        except Exception as e:
            self.status_var.set(f"截图处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.clear_screenshot_preview()
            self.toggle_screenshot_mode()

    def show_screenshot_preview(self, image):
        """显示截图预览"""
        # 转换图像为PIL格式
        pil_image = Image.fromarray(image)
        
        # 调整预览大小
        max_size = 300
        ratio = min(max_size / pil_image.width, max_size / pil_image.height)
        new_size = (int(pil_image.width * ratio), int(pil_image.height * ratio))
        pil_image = pil_image.resize(new_size, Image.LANCZOS)
        
        # 显示预览
        self.preview_image = ImageTk.PhotoImage(pil_image)
        self.screenshot_preview = self.canvas.create_image(
            50, 50, anchor=NW, image=self.preview_image, tags="preview")
        
        # 5秒后自动关闭预览
        self.root.after(5000, lambda: self.canvas.delete(self.screenshot_preview))
    
    def on_mousewheel(self, event):
        """处理鼠标滚轮缩放事件"""
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
        
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        img_coords = self.canvas.coords(self.image_item)
        rel_x = (x - img_coords[0]) / self.display_scale
        rel_y = (y - img_coords[1]) / self.display_scale
        
        delta = 0
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            delta = 0.05
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            delta = -0.05
        
        new_scale = self.display_scale * (1.0 + delta)
        new_scale = max(0.05, min(3.0, new_scale))
        
        if new_scale != self.display_scale:
            self.scale_var.set(new_scale)
            self.display_scale = new_scale
            self.update_canvas()
            
            new_img_coords = self.canvas.coords(self.image_item)
            new_x = new_img_coords[0] + rel_x * self.display_scale
            new_y = new_img_coords[1] + rel_y * self.display_scale
            
            self.canvas.xview_moveto((new_x - event.x) / self.canvas.winfo_width())
            self.canvas.yview_moveto((new_y - event.y) / self.canvas.winfo_height())
    
    def on_mouse_move(self, event):
        """鼠标移动事件处理"""
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
            
        # 更新状态栏显示鼠标位置
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        img_coords = self.canvas.coords(self.image_item)
        if img_coords:
            rel_x = (x - img_coords[0]) / self.display_scale
            rel_y = (y - img_coords[1]) / self.display_scale
            
            if 0 <= rel_x < self.original_image.shape[1] and 0 <= rel_y < self.original_image.shape[0]:
                self.status_var.set(f"鼠标位置: X={int(rel_x)}, Y={int(rel_y)}")
    
    def reset_zoom(self):
        self.scale_var.set(1.0)
        self.display_scale = 1.0
        self.update_canvas()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
    
    def on_scale_change(self, event=None):
        if hasattr(self, 'original_image') and self.original_image is not None:
            self.display_scale = self.scale_var.get()
            self.update_canvas()
    
    def on_canvas_configure(self, event):
        if hasattr(self, 'image_item'):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def toggle_continuous_mode(self):
        self.continuous_mode = not self.continuous_mode
        if self.continuous_mode:
            self.btn_continuous.config(relief=SUNKEN, bg="lightblue")
            self.status_var.set("连续测量模式已启用")
        else:
            self.btn_continuous.config(relief=RAISED, bg="SystemButtonFace")
            self.status_var.set("连续测量模式已关闭")
    
    def undo_last_measurement(self):
        if self.measurements:
            self.measurements.pop()
            self.update_results_table()
            self.update_canvas()
            self.status_var.set("已撤销最后一次测量")
        else:
            self.status_var.set("没有可撤销的测量")
    
    def calculate_total(self):
        total = sum(m[4] for m in self.measurements)
        self.total_var.set(f"总计: {total:.2f} cm")
        return total
    
    def load_image(self):
        paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not paths:
            return

        self.image_paths = paths
        self.current_image_index = 0
        self.load_image_at_index(self.current_image_index)
    
    def update_canvas(self):
        if not hasattr(self, 'original_image') or self.original_image is None:
            return
        
        h, w = self.original_image.shape[:2]
        new_w = int(w * self.display_scale)
        new_h = int(h * self.display_scale)
        
        self.display_image = cv2.resize(self.original_image, (new_w, new_h))
        
        self.pil_image = Image.fromarray(self.display_image)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        
        self.canvas.delete("all")
        self.image_item = self.canvas.create_image(0, 0, anchor=NW, image=self.tk_image)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # 绘制正交参考线
        img_coords = self.canvas.coords(self.image_item)
        for y in self.horizontal_reference_lines:
            scaled_y = img_coords[1] + y * self.display_scale
            self.canvas.create_line(img_coords[0], scaled_y, 
                                   img_coords[0] + w * self.display_scale, scaled_y,
                                   fill="cyan", width=1, dash=(4,4), tags="reference_line")
        
        for x in self.vertical_reference_lines:
            scaled_x = img_coords[0] + x * self.display_scale
            self.canvas.create_line(scaled_x, img_coords[1],
                                  scaled_x, img_coords[1] + h * self.display_scale,
                                  fill="cyan", width=1, dash=(4,4), tags="reference_line")
        
        # 绘制参考线和测量线
        if self.reference_line:
            # 将参考线坐标从图像坐标转换为画布坐标
            rx1, ry1, rx2, ry2 = self.reference_line
            x1 = img_coords[0] + rx1 * self.display_scale
            y1 = img_coords[1] + ry1 * self.display_scale
            x2 = img_coords[0] + rx2 * self.display_scale
            y2 = img_coords[1] + ry2 * self.display_scale

            self.canvas.create_line(x1, y1, x2, y2, fill="blue", width=3, tags="reference")
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2 - 15,
                                    text=f"参考线: {self.entry_length.get()}cm",
                                    fill="blue", tags="reference")

        
        for i, (mx1, my1, mx2, my2, length) in enumerate(self.measurements):
            x1 = img_coords[0] + mx1 * self.display_scale
            y1 = img_coords[1] + my1 * self.display_scale
            x2 = img_coords[0] + mx2 * self.display_scale
            y2 = img_coords[1] + my2 * self.display_scale

            line_id = self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2, tags=(f"measurement_{i}", "measurement_line"))
            self.canvas.tag_bind(line_id, "<Button-3>", lambda e, idx=i: self.on_measurement_click(idx))

            self.canvas.create_text((x1+x2)//2, (y1+y2)//2 - 15,
                                    text=f"{length:.2f}cm",
                                    fill="red", tags=f"measurement_{i}")

    
    def on_measurement_click(self, index):
        if self.drawing_mode == 'measurement':
            if 0 <= index < len(self.measurements):
                del self.measurements[index]
                self.update_results_table()
                self.update_canvas()
                self.status_var.set(f"已删除测量线 #{index+1}")

    def set_mode(self, mode):
        if self.screenshot_mode:
            self.toggle_screenshot_mode()
        if self.crop_mode:
            self.toggle_crop_mode()
        
        self.drawing_mode = mode
        if mode == 'reference':
            self.status_var.set("请在图片上绘制参考线")
        else:
            if not hasattr(self, 'scale_factor') or self.scale_factor == 0:
                self.status_var.set("请先设置参考线")
                return
            self.status_var.set("请在图片上绘制测量线")
    
    def start_drawing(self, event):
        if self.screenshot_mode:
            self.add_screenshot_point(event.x, event.y)
            return
        
        if self.crop_mode:
            self.crop_start = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
            self.crop_rect = None
            return
        
        if not self.drawing_mode or not hasattr(self, 'original_image') or self.original_image is None:
            return
        
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.start_point = (x, y)
        self.current_line = None
    
    def draw_line(self, event):
        if self.screenshot_mode:
            return
        
        if self.crop_mode and self.crop_start:
            x1, y1 = self.crop_start
            x2 = self.canvas.canvasx(event.x)
            y2 = self.canvas.canvasy(event.y)
            
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
            
            self.crop_rect = self.canvas.create_rectangle(x1, y1, x2, y2, 
                                                         outline="yellow", width=2, dash=(4,4))
            return
        
        if not self.drawing_mode or not self.start_point:
            return
        
        if self.current_line:
            self.canvas.delete(self.current_line)
        
        x1, y1 = self.start_point
        x2 = self.canvas.canvasx(event.x)
        y2 = self.canvas.canvasy(event.y)
        
        color = "blue" if self.drawing_mode == 'reference' else "red"
        self.current_line = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
    
    def end_drawing(self, event):
        if self.screenshot_mode:
            return
        
        if self.crop_mode and self.crop_start:
            x1, y1 = self.crop_start
            x2 = self.canvas.canvasx(event.x)
            y2 = self.canvas.canvasy(event.y)
            
            # 确保矩形有效
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
                # 转换为图像坐标
                img_coords = self.canvas.coords(self.image_item)
                x1_img = (x1 - img_coords[0]) / self.display_scale
                y1_img = (y1 - img_coords[1]) / self.display_scale
                x2_img = (x2 - img_coords[0]) / self.display_scale
                y2_img = (y2 - img_coords[1]) / self.display_scale
                self.measurements.append((x1_img, y1_img, x2_img, y2_img, actual_length))

                
                # 确保坐标在图像范围内
                x1_img = (x1 - img_coords[0]) / self.display_scale
                y1_img = (y1 - img_coords[1]) / self.display_scale
                x2_img = (x2 - img_coords[0]) / self.display_scale
                y2_img = (y2 - img_coords[1]) / self.display_scale
                self.measurements.append((x1_img, y1_img, x2_img, y2_img, actual_length))

                
                # 裁剪图像
                cropped = self.original_image[min(y1_img,y2_img):max(y1_img,y2_img), 
                                            min(x1_img,x2_img):max(x1_img,x2_img)]
                
                # 更新当前图像为裁剪后的图像
                self.original_image = cropped
                self.cv_image = cropped.copy()
                
                # 重置测量数据
                self.reference_line = None
                self.measurements = []
                self.clear_reference_lines()
                self.update_results_table()
                
                # 更新画布显示
                self.reset_zoom()
                self.status_var.set("图像已裁剪并显示在画布上")
            
            self.crop_start = None
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
                self.crop_rect = None
            return
        
        if not self.drawing_mode or not self.start_point:
            return
        
        x1, y1 = self.start_point
        x2 = self.canvas.canvasx(event.x)
        y2 = self.canvas.canvasy(event.y)
        
        if self.drawing_mode == 'reference':
            try:
                real_length = float(self.entry_length.get())
                if real_length <= 0:
                    raise ValueError
            except ValueError:
                self.status_var.set("请输入有效的正数作为参考长度")
                return
                
            pixel_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2) / self.display_scale
            self.scale_factor = real_length / pixel_length
            
            img_coords = self.canvas.coords(self.image_item)
            rx1 = (x1 - img_coords[0]) / self.display_scale
            ry1 = (y1 - img_coords[1]) / self.display_scale
            rx2 = (x2 - img_coords[0]) / self.display_scale
            ry2 = (y2 - img_coords[1]) / self.display_scale
            self.reference_line = (rx1, ry1, rx2, ry2)
            self.status_var.set(f"参考线已设置。比例: 1像素 = {self.scale_factor:.6f}厘米")
            self.update_canvas()
        else:
            if not hasattr(self, 'scale_factor') or self.scale_factor == 0:
                self.status_var.set("请先设置参考线")
                return
                
            pixel_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2) / self.display_scale
            actual_length = pixel_length * self.scale_factor
            img_coords = self.canvas.coords(self.image_item)
            mx1 = (x1 - img_coords[0]) / self.display_scale
            my1 = (y1 - img_coords[1]) / self.display_scale
            mx2 = (x2 - img_coords[0]) / self.display_scale
            my2 = (y2 - img_coords[1]) / self.display_scale
            self.measurements.append((mx1, my1, mx2, my2, actual_length))
            self.update_results_table()
            self.update_canvas()
        
        if not self.continuous_mode or self.drawing_mode == 'reference':
            self.drawing_mode = None
        
        self.start_point = None
        self.current_line = None
    
    def update_results_table(self):
        self.results_table.delete(*self.results_table.get_children())
        for i, (_, _, _, _, length) in enumerate(self.measurements, 1):
            self.results_table.insert("", "end", values=(f"{length:.2f} cm",))
        
        self.calculate_total()
    
    def clear_measurements(self):
        self.measurements = []
        self.update_results_table()
        self.update_canvas()
        self.status_var.set("测量结果已清除")
    
    def on_middle_button_press(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_middle_button_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

if __name__ == "__main__":
    root = Tk()
    app = EnhancedImageMeasurementApp(root)
    root.mainloop()
