import pathlib
import typing

from PIL import Image, ImageDraw, ImageOps

class Artist():
    def __init__(self, print_settings:dict, preview_settings:dict) -> None:
        self.print_settings = print_settings
        self.preview_settings = preview_settings
        self.image = None
        self.image_path = None
        self.image_preview = None
        self.image_resized = None
        self.shapes = None

    def load_image(self, image_path:pathlib.Path) -> None:
        self.image = Image.open(image_path)
        self.image_path = image_path
        unit_size = self.print_settings['density']/100 * max(self.image.width, self.image.height)
        self.image_resized = ImageOps.grayscale(self.image)
        self.image_resized = self.image_resized.resize((int(self.image_resized.width/unit_size), int(self.image_resized.height/unit_size)))
        if self.print_settings['flip x']:
            self.image_resized.transpose(Image.FLIP_LEFT_RIGHT)
        if self.print_settings['flip y']:
            self.image_resized.transpose(Image.FLIP_TOP_BOTTOM)
        self.shapes = []
        for y in range(self.image_resized.height):
            for x in range(self.image_resized.width):
                image_value = ((255-self.image_resized.getpixel((x, y)))/255)**0.5
                if image_value > 0:
                    self.shapes.append((x,y,image_value))
        print(f'{len(self.shapes)} dots generated')

    def show_preview(self) -> None:
        cell_size_pixels = (self.preview_settings['pixels'] / max(self.image_resized.width, self.image_resized.height))
        preview_size = (
            int(self.image_resized.width * cell_size_pixels),
            int(self.image_resized.height * cell_size_pixels)
        )
        self.image_preview = Image.new('RGB', preview_size, color = self.preview_settings['background'])
        draw = ImageDraw.Draw(self.image_preview)
        for shape in self.shapes:
                draw.ellipse([
                    ((shape[0]+0.5)*cell_size_pixels-(cell_size_pixels/2)*shape[2], (shape[1]+0.5)*cell_size_pixels-(cell_size_pixels/2)*shape[2]),
                    ((shape[0]+0.5)*cell_size_pixels+(cell_size_pixels/2)*shape[2], (shape[1]+0.5)*cell_size_pixels+(cell_size_pixels/2)*shape[2]),
                ], fill = self.preview_settings['color'])
        if self.print_settings['flip x']:
            self.image_preview.transpose(Image.FLIP_LEFT_RIGHT)
        if self.print_settings['flip y']:
            self.image_preview.transpose(Image.FLIP_TOP_BOTTOM)
        self.image_preview.show()

    def generate_gcode(self, frame_file:bool = True):
        cell_size_inches = (self.print_settings['size'] / max(self.image_resized.width, self.image_resized.height))
        xy_speed = self.print_settings['xy speed'] * 60
        z_speed = self.print_settings['z speed'] * 60
        t_height = self.print_settings['travel height'] * 25.4
        with open(f'{self.image_path.stem}.gcode', 'w') as file:
            self._write_settings_as_comment(file)
            file.write('G90 ; Set all axes to absolute\n')
            file.write('\n')
            file.write(f'G0 Z{t_height:0.3f} F{z_speed:0.0f}\n') # move to t height
            file.write('\n')
            for shape in self.shapes:
                x = cell_size_inches*shape[0] * 25.4
                y = cell_size_inches*shape[1] * 25.4
                z = self.print_settings['stroke']*shape[2] * 25.4
                file.write(f'G0 X{x:0.3f} Y{y:0.3f} F{xy_speed:0.0f}\n') # move to x y position
                file.write(f'G0 Z{-z:0.3f} F{z_speed:0.0f}\n') # move down
                file.write(f'G0 Z{t_height:0.3f} F{z_speed:0.0f}\n') # move to t height
                file.write('\n')
            file.write(f'G0 X0.000 Y0.000 F{xy_speed:0.0f}\n') # move to x y position
        if frame_file:
            x_max = cell_size_inches*(self.image_resized.width-1) * 25.4
            y_max = cell_size_inches*(self.image_resized.height-1) * 25.4
            z = self.print_settings['stroke']*0.5 * 25.4
            with open(f'{self.image_path.stem} frame.gcode', 'w') as file:
                self._write_settings_as_comment(file)
                file.write('G90 ; Set all axes to absolute\n')
                file.write('\n')
                file.write(f'G0 Z{t_height:0.3f} F{z_speed:0.0f}\n') # move to t height
                file.write('\n')
                for x,y in [(0,0), (x_max,0), (x_max,y_max), (0,y_max)]:
                    file.write(f'G0 X{x:0.3f} Y{y:0.3f} F{xy_speed:0.0f}\n') # move to x y position
                    file.write(f'G0 Z{-z:0.3f} F{z_speed:0.0f}\n') # move down
                    file.write(f'G0 Z{t_height:0.3f} F{z_speed:0.0f}\n') # move up
                    file.write('\n')
                dots = 15
                for i in range(1, dots+1):
                    x = i * cell_size_inches * 25.4
                    y = 0
                    z = ((i/dots)**0.5)
                    file.write(f'G0 X{x:0.3f} Y{y:0.3f} F{xy_speed:0.0f}\n') # move to x y position
                    file.write(f'G0 Z{-z:0.3f} F{z_speed:0.0f}\n') # move down
                    file.write(f'G0 Z{t_height:0.3f} F{z_speed:0.0f}\n') # move up
                    file.write('\n')
                file.write(f'G0 X0.000 Y0.000 F{xy_speed:0.0f}\n') # move to x y position

    def _write_settings_as_comment(self, file_obj:typing.TextIO):
        file_obj.write(f'; {len(self.shapes)} DOTS\n')
        file_obj.write('\n')
        file_obj.write('; PRINT SETTINGS\n')
        for k,v in self.print_settings.items():
            file_obj.write(f'; {k} = {v}\n')
        file_obj.write('\n')

if __name__ == '__main__':
    print_settings = { 
        'size': 7,              # units inches
        'density': 0.75,        # percentage points
        'stroke': 0.015,         # dot stroke amount in inches
        'xy speed': 150,         # mm/s
        'z speed': 15,           # mm/s
        'travel height': 0.025,   # inches
        'flip x': True,
        'flip y': False,
    }

    preview_settings = {
        'background': (255, 255, 255),  # RGB
        'color': (0, 0, 0),             # RGB
        'pixels': 5000,                 # Maximum edge length in pixels
    }

    tool = Artist(
        print_settings=print_settings,
        preview_settings=preview_settings,
    )

    tool.load_image(pathlib.Path('images','colored_test3.jpg'))

    tool.show_preview()
    tool.generate_gcode()