from panda3d.core import *
#we need to read the config before we go on
import configparser
Config = configparser.ConfigParser()
Config.read('config.ini')
#read all options as prc_file_data in case they have p3d meaning
for section in Config.sections():
    for option in Config.options(section):
        loadPrcFileData("", option +' '+Config.get(section, option))
load_prc_file_data('','textures-power-2 None')

from direct.showbase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.gui.DirectGui import *
from direct.interval.FunctionInterval import Func, Wait
from direct.interval.MetaInterval import Sequence, Parallel
from direct.interval.LerpInterval import LerpPosInterval, LerpHprInterval

import io
import os
import sys
import json
import time
import shutil
import random
import math
import builtins
from collections import OrderedDict
from time import gmtime, strftime
from itertools import islice
import string

from camera import CameraControler
from loading_screen import loading
from gui import UI

#set the window decoration before we start
wp = WindowProperties.getDefault()
wp.set_title("THG by wezu.dev@gmail.com")
wp.set_icon_filename('gui/icon.ico')
WindowProperties.set_default(wp)

def encode_value(i):
    '''Encode int value to uv offset'''
    ones=(abs(i)%10)*0.1
    tens=(abs(i)//10)*0.1
    sign=1.0
    if i<0:
        sign=-1.0
    return Vec3(tens,ones,sign)

class App(DirectObject):
    def __init__(self):
        builtins.app=self
        builtins.Config = Config
        #basic stuff
        self.base = ShowBase.ShowBase()
        self.base.disableMouse()
        self.base.set_background_color(0, 0, 0)
        # listen to window events
        self.accept("window-event", self._on_window_event)

        #set some shader inputs
        screen_size = Vec2(base.win.get_x_size(), base.win.get_y_size())
        render.set_shader_input('screen_size', screen_size)
        render.set_shader_input("camera_pos", base.cam.get_pos(render))

        with loading():
            #make the gui
            self.gui=UI('gui/anonymous.ttf',
                       'gui/moonhouse.ttf',
                       'gui/monosb.ttf' )
            self.gui.load_from_file('gui/gui.json')
            self.gui.show_hide('main_menu')

            #load the music
            self.music=loader.load_music('music/starflash.ogg')
            self.music.set_loop(True)
            self.music.set_loop_count(0)
            #load sounds
            self.sfx={}
            self.sfx['up']=loader.load_sfx('sounds/up.ogg')
            self.sfx['down']=loader.load_sfx('sounds/down.ogg')
            self.sfx['yay']=loader.load_sfx('sounds/yay.ogg')

            #set volume
            self.music_volume=Config.getfloat('audio', 'music-volume')
            self.sound_volume=Config.getfloat('audio', 'sound-volume')
            base.musicManager.setVolume(self.music_volume)
            base.sfxManagerList[0].setVolume(self.sound_volume)
            self.gui['sound-volume1']['value']=self.sound_volume
            self.gui['music-volume1']['value']=self.music_volume
            self.gui['sound-volume2']['value']=self.sound_volume
            self.gui['music-volume2']['value']=self.music_volume

            #setup key binds for the camera
            self.key_binds={}
            self.key_binds['rotate']=Config.get('keys', 'camera-rotate')
            self.key_binds['pan']=Config.get('keys', 'camera-pan')
            self.key_binds['zoom_in']=Config.get('keys', 'camera-zoom-in')
            self.key_binds['zoom_out']=Config.get('keys', 'camera-zoom-out')
            self.key_binds['left']=Config.get('keys', 'camera-left')
            self.key_binds['right']=Config.get('keys', 'camera-right')
            self.key_binds['forward']=Config.get('keys', 'camera-forward')
            self.key_binds['back']=Config.get('keys', 'camera-back')
            cam_speed=Config.getfloat('control', 'camera-speed')
            cam_zoom_speed=Config.getfloat('control', 'zoom-speed')
            self.cam_driver=CameraControler(pos=(0,0,0), offset=(0, 20, 0),
                                            speed=cam_speed, zoom_speed=cam_zoom_speed)
            self.cam_driver.bind_keys(**self.key_binds)

            #setup clicking on 3d objects
            self.ray_trav = CollisionTraverser()
            self.ray_handler = CollisionHandlerQueue()
            picker_np = base.camera.attach_new_node(CollisionNode('mouseRay'))
            self.mouse_ray = CollisionRay()
            picker_np.node().add_solid(self.mouse_ray)
            self.ray_trav.add_collider(picker_np, self.ray_handler)

            #skybox
            self.skybox=loader.load_model('models/stars')
            self.skybox.reparent_to(render)
            self.skybox.set_scale(0.8)
            self.skybox.set_bin('background', 0)
            self.skybox.set_depth_write(0)
            self.skybox.set_light_off()
            self.skybox.set_transparency(TransparencyAttrib.M_none)

            self.stars0=self.make_stars(number=1000, size=8, color_variation=0.5, sigma=2.0, spread=10)
            self.stars1=self.make_stars(number=800, size=8, texture='tex/star2.png', sigma=3.0, spread=20)
            self.stars2=self.make_stars(number=300, size=24, spread=50)
            self.stars3=self.make_stars(number=100, size=32, color_variation=0.4, spread=100)
            self.stars4=self.make_stars(number=100, size=56, color_variation=0.2, spread=150)
            self.stars5=self.make_stars(number=10, size=120, color_variation=0.1, spread=100)

            LerpHprInterval(nodePath=self.stars0,duration=2000.0, hpr=(360,360,360), startHpr=(0,0,0)).loop()
            LerpHprInterval(nodePath=self.stars1,duration=2400.0, hpr=(360,360,360), startHpr=(0,0,0)).loop()
            LerpHprInterval(nodePath=self.stars2,duration=2700.0, hpr=(360,360,360), startHpr=(0,0,0)).loop()
            LerpHprInterval(nodePath=self.stars3,duration=3100.0, hpr=(360,360,360), startHpr=(0,0,0)).loop()
            LerpHprInterval(nodePath=self.stars4,duration=3700.0, hpr=(360,360,360), startHpr=(0,0,0)).loop()

            self.accept('mouse1', self.on_click)
            self.accept('mouse3', self.on_click, [True])
            self.time=0
            taskMgr.add(self.update, 'update_tsk')
            self.clock_tsk=taskMgr.doMethodLater(1.0, self.clock, 'clock_tsk')

        #everything is loaded, show it and start the music
        self.gui.fade_screen(0.5, base.get_background_color())
        self.music.play()

    def do_nill(self):
        pass

    def start_game(self, difficulty=0):
        if difficulty<0:
            self.gui.show_hide(['help_img','help_txt'])
        spread=1.5
        if difficulty>5:
            spread=2.0
        elif difficulty>7:
            spread=4.0
        self.make_graph(pow(2, 3+difficulty), spread)
        self.cam_driver.node.set_pos(render, (0,0,0))
        self.cam_driver.node.set_h(45)
        self.cam_driver.gimbal.set_p(45)
        self.gui.show_hide(['menu_button','win_ss_button'], 'new_game_menu')
        self.moves=[]
        self.time=0


    def make_graph(self, count=10, spread=1.5):
        #make a format with a vertid column
        array = GeomVertexArrayFormat()
        array.add_column("vertex", 3, Geom.NTFloat32, Geom.CPoint)
        array.add_column("vertid", 4, Geom.NT_uint16, Geom.C_index)
        vert_format = GeomVertexFormat()
        vert_format.add_array(array)
        vert_format = GeomVertexFormat.register_format(vert_format)
        #make the vertex data
        vdata = GeomVertexData('points', vert_format, Geom.UHDynamic)
        vertex  = GeomVertexWriter(vdata, 'vertex')
        vertid  = GeomVertexWriter(vdata, 'vertid')

        #biased honeycomb structure
        randomish_points=[Point3(0,0,1),
                         Point3(-1, 0,0),
                         Point3(0.5,0.866,0),
                         Point3(0.5,-0.866,0),
                         Point3(-1, 0,0),
                         Point3(0.5,0.866,0),
                         Point3(0.5,-0.866,0)
                         ]
        points=[(0,0,0)]
        oddity=[1]
        odd=1
        while len(points)<count:
            point=Point3(random.choice(randomish_points))*odd*spread
            point+=Point3(*points[-1])
            point=tuple([round(i,3) for i in point])
            if not point in points:
                points.append(point)
                oddity.append(odd)
                odd*=-1
            else: #make a branch
                while point in points:
                    i=random.randint(0,len(points)-1)
                    odd=-oddity[i]
                    point=Point3(*points[i])+Point3(random.choice(randomish_points))*odd*spread
                    point=tuple([round(i,3) for i in point])
                points.append(point)
                oddity.append(odd)

        #populate the vertex data
        for i, point in enumerate(points):
            vertex.addData3f(Point3(*point))
            vertid.addData4f(Vec4(i, 0, 0, 0))

        #make it into a geom/node
        geo_points = GeomPoints(Geom.UHDynamic)
        geo_points.add_next_vertices(count)
        geo_points.close_primitive()
        geo = Geom(vdata)
        geo.add_primitive(geo_points)
        gnode = GeomNode('points')
        gnode.add_geom(geo)

        #make the graph
        self.graph=OrderedDict()
        for i, point in enumerate(points):
            self.graph[point]=set()
            for p in points:
                distance=(Vec3(*point)-Vec3(*p)).length()
                if distance<1.1*spread:
                    self.graph[point].add(p)
        #draw lines, count connections
        l=LineSegs()
        l.set_thickness(3.0)
        edges=set()
        for origin, points in self.graph.items():
            for target in points:
                edge=frozenset((origin,target))
                if edge not in edges and len(edge)>1:
                    edges.add(edge)
                    midpoint=((origin[0]+target[0])*0.5,
                             (origin[1]+target[1])*0.5,
                             (origin[2]+target[2])*0.5)
                    l.move_to(origin)
                    l.draw_to(midpoint)
                    l.draw_to(target)
        line_node=l.create()
        for i in range(l.get_num_vertices()):
            v=tuple([round(i,3) for i in l.get_vertex(i)])
            if v in self.graph:
                l.set_vertex_color(i, 1.0, 1.0, 1.0, 0.0)
            else:
                l.set_vertex_color(i, 0.8, 0.8, 0.8, 0.9)

        self.num_edges=len(edges)
        self.genus=self.num_edges-count+1
        #make random values such that their sum is 0
        values=list(range(count))
        random.shuffle(values)
        last_random=random.randint(0,3)
        self.values=list(range(count))
        for i,v in enumerate(values):
            if i%2==0:
                self.values[v]=-last_random
            else:
                last_random=random.randint(0,3)
                self.values[v]=last_random

        #make it winnable
        while(sum(self.values)<self.genus):
            i=random.randint(0,len(self.values)-1)
            self.values[i]+=1
        #make sure there's at leas 1 negative node
        has_negative=False
        for v in self.values:
            if v<0:
                has_negative=True
                break
        if not has_negative:
            v=self.values[0]
            self.values[0]=-1
            self.values[1]+=v+1

        #copy the values into a texture
        self.values_pfm=PfmFile()
        self.values_pfm.clear(x_size=count, y_size=1, num_channels=3)
        for i, v in enumerate(self.values):
            self.values_pfm.set_point3(i, 0, encode_value(v))

        #try to remove existing nodes
        try:
            self.nodes_np.remove_node()
            self.lines_np.remove_node()
            self.collisions.remove_node()
        except:
            pass
        #make the actual nodes
        self.nodes_np = render.attach_new_node(gnode)
        self.nodes_np.set_render_mode(RenderModeAttrib.MPoint, 1.0)
        shader_attrib = ShaderAttrib.make(Shader.load(Shader.SLGLSL, 'shaders/node_v.glsl', 'shaders/node_f.glsl'))
        shader_attrib = shader_attrib.set_flag(ShaderAttrib.F_shader_point_size, True)
        self.nodes_np.set_attrib(shader_attrib)
        self.value_tex=Texture()
        self.value_tex.load(self.values_pfm)
        self.nodes_np.set_shader_input('value_tex', self.value_tex)
        self.nodes_np.set_shader_input('text_tex',loader.load_texture('tex/numbers_blur.png') )
        self.nodes_np.set_shader_input('base_tex',loader.load_texture('tex/ball.png') )
        self.nodes_np.set_transparency(TransparencyAttrib.M_alpha)
        #attach lines
        self.lines_np=render.attach_new_node(line_node)
        self.lines_np.set_transparency(TransparencyAttrib.M_alpha)
        self.lines_np.set_antialias(AntialiasAttrib.MLine)
        self.lines_np.set_shader_off(1)

        #make collisions
        self.collisions=render.attach_new_node('collisions')
        self.value_lookup={}
        #py3 has ordered dict so we can do this
        for id, (point, connections) in enumerate(self.graph.items()):
            cs = CollisionSphere(point, 0.25)
            cnode = self.collisions.attach_new_node(CollisionNode('cnode'))
            cnode.node().add_solid(cs)
            cnode.set_python_tag('point', point)
            cnode.set_python_tag('id', id)
            self.value_lookup[point]=id

    def make_stars(self, number, size,
                color_variation=0.3, texture='tex/star1.png',
                sigma=0.5, spread=100.0):
        vdata = GeomVertexData('points', GeomVertexFormat.getV3c4(), Geom.UHDynamic)
        vertex  = GeomVertexWriter(vdata, 'vertex')
        vcolor = GeomVertexWriter(vdata, 'color')

        color=(random.uniform(1.0-color_variation, 1.0),  1.0-color_variation, random.uniform(1.0-color_variation, 1.0))
        for i in range(number):
            vertex.addData3f(random.gauss(0, sigma)*spread,
                              random.gauss(0, sigma)*spread,
                              random.gauss(0, sigma)*spread)
            vcolor.addData3f(*color)
            if i%10==0:
                color=(random.uniform(1.0-color_variation, 1.0),  1.0-color_variation, random.uniform(1.0-color_variation, 1.0))

        points = GeomPoints(Geom.UHDynamic)
        points.add_next_vertices(number)
        points.close_primitive()
        geo = Geom(vdata)
        geo.add_primitive(points)
        gnode = GeomNode('points')
        gnode.add_geom(geo)
        np = render.attach_new_node(gnode)
        np.set_tex_gen(TextureStage.getDefault(), TexGenAttrib.MPointSprite)
        np.set_texture(loader.load_texture(texture))
        np.set_render_mode_thickness(size)
        self.set_additive_blend(np)
        return np

    def set_additive_blend(self, node):
        color_attrib = ColorBlendAttrib.make(ColorBlendAttrib.M_add,
                                             ColorBlendAttrib.O_incoming_alpha,
                                             ColorBlendAttrib.O_one )
        node.set_attrib(color_attrib)
        node.set_bin("fixed", 0)
        node.set_depth_test(True)
        node.set_depth_write(False)

    def on_click(self, is_right_click=False):
        if base.mouseWatcherNode.has_mouse():
            mpos = base.mouseWatcherNode.get_mouse()
            self.mouse_ray.set_from_lens(base.camNode, mpos.get_x(), mpos.get_y())
            self.ray_trav.traverse(render)
            if self.ray_handler.get_num_entries() > 0:
                self.ray_handler.sort_entries()
                hit = self.ray_handler.get_entry(0).get_into_node_path()
                id=hit.get_python_tag('id')
                point=hit.get_python_tag('point')
                self.change_value(id, point, is_right_click)



    def change_value(self, id, point, down=True):
        if down:
            self.sfx['down'].play()
        else:
            self.sfx['up'].play()
        amount=0
        for neighbour in self.graph[point]:
            neighbour_id=self.value_lookup[neighbour]
            if neighbour_id!= id:
                if down:
                    self.values[neighbour_id]+=1
                    amount+=1
                else:
                    self.values[neighbour_id]-=1
                    amount-=1
                self.values_pfm.set_point3(neighbour_id, 0, encode_value(self.values[neighbour_id]))
        self.values[id]-=amount
        self.values_pfm.set_point3(id, 0, encode_value(self.values[id]))
        self.value_tex.load(self.values_pfm)
        if self.moves:
            if self.moves[-1] != (id,down) :
                self.moves.append((id,down))
        else:
            self.moves.append((id,down))
        #check winning condition
        win=True
        for v in self.values:
            if v<0:
                win=False
                break
        if win:
            self.gui.show_hide('game_over', ['help_img','help_txt', 'menu_button'])
            self.collisions.remove_node()
            self.sfx['yay'].play()
            t=self.get_time()
            feedback={'genus':self.genus,
                      'moves':len(self.moves),
                      'nodes':len(self.values),
                      'edges':self.num_edges,
                      'h':t[0],
                      'm':t[1],
                      's':t[2]}
            pat= '   Graph Genus:   {genus}\n'
            pat+='   Graph Nodes:   {nodes}\n'
            pat+='   Graph Edges:   {edges}\n'
            pat+='   Time taken:    {h:02d}:{m:02d}:{s:02d}\n'
            pat+='   Moves made:    {moves}\n'
            self.gui['win_txt'].set_text(pat.format(**feedback))

    def get_time(self):
        s=self.time
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return (h,m,s)

    def clock(self, task):
        self.time+=1
        return task.again

    def update(self, task):
        render.set_shader_input("camera_pos", base.cam.get_pos(render))
        self.skybox.set_pos(self.cam_driver.node.get_pos(render))
        return task.again

    def save_screen(self):
        self.gui.show_hide('', ['win_exit_button', 'win_ss_button', 'win_new_button'])
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        base.screenshot(namePrefix = 'screenshot/win')
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        self.gui.show_hide(['win_exit_button', 'win_new_button'])
        txt=self.gui['win_txt'].get_text()
        txt+='\n     Screenshot saved'
        self.gui['win_txt'].set_text(txt)

    def set_sound_volume(self, volume):
        self.sound_volume=volume
        base.sfxManagerList[0].setVolume(self.sound_volume)
        Config.set('audio', 'sound-volume', str(self.sound_volume))

    def set_music_volume(self, volume):
        self.music_volume=volume
        base.musicManager.setVolume(self.music_volume)
        Config.set('audio', 'music-volume', str(self.music_volume))

    def exit_to_main(self):
        try:
            self.nodes_np.remove_node()
            self.lines_np.remove_node()
            self.collisions.remove_node()
        except:
            pass
        self.gui.show_hide('main_menu',['help_txt','help_img', 'in_game_menu'])

    def save_to_file(self):
        filename=self.gui['save_input'].get()+'.json'
        safechars = bytearray(('_-.( )' + string.digits + string.ascii_letters).encode())
        allchars = bytearray(range(0x100))
        deletechars = bytearray(set(allchars) - set(safechars))
        safe_filename = filename.encode('ascii', 'ignore').translate(None, deletechars).decode()
        data={'values':self.values,
              'graph_keys':list(self.graph.keys()),
              'graph_values':[list(v) for v in self.graph.values()],
              'time':self.time,
              'moves':self.moves
              }
        with open('save/'+safe_filename, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        self.gui.show_hide('menu_button','save_menu')

    def load_from_file(self, file_name):
        #try to remove existing nodes
        try:
            self.nodes_np.remove_node()
            self.lines_np.remove_node()
            self.collisions.remove_node()
        except:
            pass
        with open(file_name) as f:
            data = json.load(f)

        points=data['graph_keys']
        count=len(data['graph_keys'])
        graph_keys=[tuple(v) for v in data['graph_keys']]
        graph_values=[[tuple(j) for j in i] for i in data['graph_values']]
        self.graph=OrderedDict(zip(graph_keys, graph_values))
        self.values=data['values']
        self.time=data['time']
        self.moves=data['moves']
        #make a format with a vertid column
        array = GeomVertexArrayFormat()
        array.add_column("vertex", 3, Geom.NTFloat32, Geom.CPoint)
        array.add_column("vertid", 4, Geom.NT_uint16, Geom.C_index)
        vert_format = GeomVertexFormat()
        vert_format.add_array(array)
        vert_format = GeomVertexFormat.register_format(vert_format)
        #make the vertex data
        vdata = GeomVertexData('points', vert_format, Geom.UHDynamic)
        vertex  = GeomVertexWriter(vdata, 'vertex')
        vertid  = GeomVertexWriter(vdata, 'vertid')

        #populate the vertex data
        for i, point in enumerate(points):
            vertex.addData3f(Point3(*point))
            vertid.addData4f(Vec4(i, 0, 0, 0))

        #make it into a geom/node
        geo_points = GeomPoints(Geom.UHDynamic)
        geo_points.add_next_vertices(count)
        geo_points.close_primitive()
        geo = Geom(vdata)
        geo.add_primitive(geo_points)
        gnode = GeomNode('points')
        gnode.add_geom(geo)

        #draw lines, count connections
        l=LineSegs()
        l.set_thickness(3.0)
        edges=set()
        for origin, points in self.graph.items():
            for target in points:
                edge=frozenset((origin,target))
                if edge not in edges and len(edge)>1:
                    edges.add(edge)
                    midpoint=((origin[0]+target[0])*0.5,
                             (origin[1]+target[1])*0.5,
                             (origin[2]+target[2])*0.5)
                    l.move_to(origin)
                    l.draw_to(midpoint)
                    l.draw_to(target)
        line_node=l.create()
        for i in range(l.get_num_vertices()):
            v=tuple([round(i,3) for i in l.get_vertex(i)])
            if v in self.graph:
                l.set_vertex_color(i, 1.0, 1.0, 1.0, 0.0)
            else:
                l.set_vertex_color(i, 0.8, 0.8, 0.8, 0.9)

        self.num_edges=len(edges)
        self.genus=self.num_edges-count+1

        #copy the values into a texture
        self.values_pfm=PfmFile()
        self.values_pfm.clear(x_size=count, y_size=1, num_channels=3)
        for i, v in enumerate(self.values):
            self.values_pfm.set_point3(i, 0, encode_value(v))

        #make the actual nodes
        self.nodes_np = render.attach_new_node(gnode)
        self.nodes_np.set_render_mode(RenderModeAttrib.MPoint, 1.0)
        shader_attrib = ShaderAttrib.make(Shader.load(Shader.SLGLSL, 'shaders/node_v.glsl', 'shaders/node_f.glsl'))
        shader_attrib = shader_attrib.set_flag(ShaderAttrib.F_shader_point_size, True)
        self.nodes_np.set_attrib(shader_attrib)
        self.value_tex=Texture()
        self.value_tex.load(self.values_pfm)
        self.nodes_np.set_shader_input('value_tex', self.value_tex)
        self.nodes_np.set_shader_input('text_tex',loader.load_texture('tex/numbers_blur.png') )
        self.nodes_np.set_shader_input('base_tex',loader.load_texture('tex/ball.png') )
        self.nodes_np.set_transparency(TransparencyAttrib.M_alpha)
        #attach lines
        self.lines_np=render.attach_new_node(line_node)
        self.lines_np.set_transparency(TransparencyAttrib.M_alpha)
        self.lines_np.set_antialias(AntialiasAttrib.MLine)
        self.lines_np.set_shader_off(1)

        #make collisions
        self.collisions=render.attach_new_node('collisions')
        self.value_lookup={}
        #py3 has ordered dict so we can do this
        for id, (point, connections) in enumerate(self.graph.items()):
            cs = CollisionSphere(point, 0.25)
            cnode = self.collisions.attach_new_node(CollisionNode('cnode'))
            cnode.node().add_solid(cs)
            cnode.set_python_tag('point', point)
            cnode.set_python_tag('id', id)
            self.value_lookup[point]=id

        self.cam_driver.node.set_pos(render, (0,0,0))
        self.cam_driver.node.set_h(45)
        self.cam_driver.gimbal.set_p(45)
        self.gui.show_hide(['win_ss_button','menu_button'],'load_menu')

    def show_save_menu(self):
        self.gui.show_hide('save_menu', 'in_game_menu')
        self.gui['save_input'].set(strftime("save %Y-%m-%d %H.%M", gmtime()))

    def show_load_menu(self):
        self.gui.show_hide('load_menu', 'main_menu')
        try:
            for button_name in self.load_buttons:
                self.gui.remove_button(button_name)
        except:
            pass
        self.load_buttons=[]
        for fn in os.listdir('save'):
            f=Filename(fn)
            self.load_buttons.append('button_'+fn)
            app.gui.button(txt='{name:<40}'.format(name=f.getBasenameWoExtension()),
                                   sort_dict={'name':fn},
                                   cmd='app.load_from_file("save/'+fn+'")',
                                   width=256,
                                   pos=(33,0),
                                   name='button_'+fn,
                                   parent='load_menu_canvas')
        self.gui.sort_buttons('load_menu_canvas', 'name', False)


    def exit(self):
        with open('config.ini', 'w') as config_filename:
            Config.write(config_filename)
        base.destroy()
        os._exit(1)

    def _on_window_event(self, window):
        """
        Function called when something hapens to the main window
        """
        if window is not None:
            screen_size = Vec2(base.win.get_x_size(), base.win.get_y_size())
            render.set_shader_input('screen_size', screen_size)

application=App()
application.base.run()

