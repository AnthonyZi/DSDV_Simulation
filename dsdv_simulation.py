import tkinter as tk
import time
import threading
import random
import math
import json

class RoutingTable(object):
    def __init__(self, node):
        self.node = node
        self.routes_dict = dict()
        self.seq_number = random.randint(0,100)*2
        self.routes_dict[self.node.node_id] = [self.node.node_id, 0, self.seq_number, int(time.time())]

    def compare_routes(self,my_route,external_route):
        metric1 = my_route[0]
        seq_num1 = my_route[1]
        metric2 = external_route[0]+1
        seq_num2 = external_route[1]

        if seq_num1 == seq_num2:   # equal freshness
            if metric1 <= metric2: # shorter route is my_route
                return 0
            else:
                return 1

        if seq_num1 > seq_num2:    # my_route is fresher
            return 0
        else:
            return 1


    def update(self, routing_table_update_string):
        updated = False
        other_routes = self.recv_string_decode(routing_table_update_string)
        for k in other_routes.keys():
            k_int = int(k)
            other_route = other_routes[k]
            other_entry_inf = (other_route[1],other_route[2])
            if k_int in self.routes_dict.keys():
                my_route = self.routes_dict[k_int]
                my_entry_inf = (my_route[1],my_route[2])
                better_route = self.compare_routes(my_entry_inf,other_entry_inf)
                if better_route == 1:
                    self.routes_dict[k_int] = [other_route[0],other_route[1]+1,other_route[2],int(time.time())]
                    updated = True
            else:
                self.routes_dict[k_int] = [other_route[0],other_route[1]+1,other_route[2],int(time.time())]
                updated = True

        return updated


    def recv_string_decode(self, routes_string):
        return json.loads(routes_string)

    def send_string_encode(self):
        send_dict = dict()
        for k in self.routes_dict.keys():
            next_hop,metric,dst_seq_num,install_time = self.routes_dict[k]
            send_dict[k] = [self.node.node_id, metric, dst_seq_num]
        return json.dumps(send_dict)

    def to_string(self):
#        print(self.routes_dict)
        out  = "##### Routing Table for #{:<3} ######".format(self.node.node_id)
        out += "\n"
        out += "|DestID|NextHop|Metric|SeqNo|InstT|"
        for k in sorted(self.routes_dict.keys()):
            out += "\n"
            next_hop,metric,dst_seq_num,install_time = self.routes_dict[k]
            out += "|{:<6}|{:<7}|{:<6}|{:<5}|{:<5}|".format(k,next_hop,metric,dst_seq_num,install_time%100000)
        return out

class Node(object):
    def __init__(self, simulation_canvas, width, cor_x, cor_y, tx_range, node_id):
        self.simulation_canvas = simulation_canvas
        self.width = width
        self.cor_x = cor_x
        self.cor_y = cor_y
        self.tx_range = tx_range
        self.node_id = node_id

        self.edges = []

        self.routing_table = RoutingTable(self)

#        self.periodic_update_range = (20,30) # up to 1 second
#        self.periodic_update_range = (2,3) # using iteration_step-button
        self.periodic_update_range = (10,20) # using iteration_step-button
        self.reset_periodic_update_counter()

        self.colorised_counter = -1
        self.fill_colour = "blue"

        self.draw_entity(self.cor_x,self.cor_y)

    def remove_entity(self):
        self.simulation_canvas.canvas.delete(self.entity)
        self.simulation_canvas.canvas.delete(self.entity_text)

    def draw_entity(self,cor_x,cor_y):
        self.entity = self.simulation_canvas.canvas.create_oval(cor_x-self.width/2,cor_y-self.width/2,cor_x+self.width/2,cor_y+self.width/2, fill="cyan")
        self.entity_text = self.simulation_canvas.canvas.create_text(cor_x,cor_y,text=str(self.node_id))

    def redraw_entity(self,cor_x,cor_y):
        self.remove_entity()
        self.draw_entity(cor_x,cor_y)
        for edge in self.edges:
            edge.redraw_entity()

    def reset_periodic_update_counter(self):
        self.periodic_update_counter = random.randint(*self.periodic_update_range)

    def get_distance(self, posxy):
        x,y = posxy
        return math.hypot(self.cor_x-x,self.cor_y-y)

    def update_step(self):
        if self.periodic_update_counter == 0:
            self.send(self.routing_table.send_string_encode())
            self.reset_periodic_update_counter()
        self.periodic_update_counter -= 1

        if self.colorised_counter >= 0:
            if self.colorised_counter == 0:
                self.simulation_canvas.canvas.itemconfigure(self.entity, fill=self.fill_colour)
            self.colorised_counter -= 1



    def routing_table_access(self, received_table_string):
        return self.routing_table.update(received_table_string)

    def send(self,message):
        self.simulation_canvas.medium_access(self,message,self.tx_range)

    def receive(self,message):
        routing_table_change = self.routing_table_access(message)
        self.periodic_update_counter = 0 if routing_table_change else self.periodic_update_counter

    def colorise(self,fill):
        self.simulation_canvas.canvas.itemconfigure(self.entity,fill=fill)
        self.colorised_counter = 1


class Edge(object):
    def __init__(self, canvas, n1, n2):
        self.canvas = canvas

        self.n1 = n1
        self.n2 = n2

        self.n1.edges.append(self)
        self.n2.edges.append(self)

        self.colorised_counter = -1
        self.fill_colour = "black"

        self.draw_entity()

    def remove_entity(self):
        self.simulation_canvas.canvas.delete(self.entity)

    def draw_entity(self):
        x1,y1 = self.n1.cor_x,self.n1.cor_y
        x2,y2 = self.n2.cor_x,self.n2.cor_y

        node_distance = math.hypot(x1-x2,y1-y2)

        begin_ratio = ((self.n2.width/2)+1)/node_distance
        end_ratio = 1-((self.n1.width/2)+1)/node_distance

        x1 = begin_ratio*x2+(1-begin_ratio)*x1
        y1 = begin_ratio*y2+(1-begin_ratio)*y1
        x2 = end_ratio*x2+(1-end_ratio)*x1
        y2 = end_ratio*y2+(1-end_ratio)*y1

        self.entity = self.canvas.create_line(x1,y1, x2,y2, width=2, fill=self.fill_colour)

    def redraw_entity(self):
        self.remove_entity()
        self.draw_entity()

    def colorise(self,fill):
        self.canvas.itemconfigure(self.entity,fill=fill)
        self.colorised_counter = 1

    def update_step(self):
        if self.colorised_counter >= 0:
            if self.colorised_counter == 0:
                self.canvas.itemconfigure(self.entity, fill=self.fill_colour)
            self.colorised_counter -= 1


#    def create_arrow(self):
#        x1 = self.nodes[0].cor_x
#        y1 = self.nodes[0].cor_y
#        x2 = self.nodes[1].cor_x
#        y2 = self.nodes[1].cor_y
#
#        node_distance = math.hypot(x1-x2,y1-y2)
#
#        begin_ratio = ((self.nodes[1].width/2)+1)/node_distance
#        end_ratio = 1-((self.nodes[0].width/2)+1)/node_distance
#
#        x1 = begin_ratio*x2+(1-begin_ratio)*x1
#        y1 = begin_ratio*y2+(1-begin_ratio)*y1
#        x2 = end_ratio*x2+(1-end_ratio)*x1
#        y2 = end_ratio*y2+(1-end_ratio)*y1
#
#        arrow_direction = math.atan2(y2-y1,x2-x1)
#
#        p1_ratio = self.arrow_tip_length/node_distance
#
#        p1x = p1_ratio*x1+(1-p1_ratio)*x2
#        p1y = p1_ratio*y1+(1-p1_ratio)*y2
#
#        left_wing_direction = arrow_direction+math.pi/2
#        right_wing_direction = arrow_direction-math.pi/2
#
#        left_wing_offset_x = math.cos(left_wing_direction)*self.arrow_tip_width/2
#        left_wing_offset_y = math.sin(left_wing_direction)*self.arrow_tip_width/2
#        right_wing_offset_x = math.cos(right_wing_direction)*self.arrow_tip_width/2
#        right_wing_offset_y = math.sin(right_wing_direction)*self.arrow_tip_width/2
#
#        p2x = p1x+left_wing_offset_x
#        p2y = p1y+left_wing_offset_y
#        p3x = p1x+right_wing_offset_x
#        p3y = p1y+right_wing_offset_y
#
#        self.entity = self.canvas.create_line(x1,y1, p1x,p1y, p2x,p2y, x2,y2, p3x,p3y, p1x,      +++p1y, width=2)

class SimulationCanvas(threading.Thread):
    def __init__(self, simulation, width, height):
        super().__init__()
        self.simulation = simulation
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(self.simulation.root, width=self.width, height=self.height, borderwidth=0, highlightthickness=0, bg="#DDD")
        self.canvas.grid(row=0, column=1, padx=10, pady=10)

        self.node_width = 30
        self.node_tx_range = 100
        self.node_min_distance = 60
        self.node_at_most_one_max_distance = 100
        self.update_rate = 10 #fps

        self.canvas.bind("<Button-1>", self.mouse_click_callback_left)
        self.canvas.bind("<Button-3>", self.mouse_click_callback_right)

        self.reset_network()
        self.time_step = 0
        self.update_step_type = 0

    def reset_network(self):
        self.canvas.delete("all")
        self.nodes = []
        self.edges = []
        self.medium_transmission_buffer = []
        self.time_step = 0

    def initialise_network(self, number_nodes):
        self.reset_network()
        self.number_nodes = number_nodes
        self.time_step_text = self.canvas.create_text(20,20, anchor=tk.NW, text="timestep: {:>3}".format(self.time_step))

        self.create_random_nodes()
        for node in self.nodes:
            self.canvas.itemconfigure(node.entity,fill="blue")

        self.connect_nodes()

    def add_node(self,cor_x,cor_y,node_id):
        new_node = Node(self, self.node_width, cor_x, cor_y, self.node_tx_range,node_id)
        self.nodes.append(new_node)

    def create_random_nodes(self):
        rand_range_x1,rand_range_x2 = self.node_width/2,self.width-self.node_width/2
        rand_range_y1,rand_range_y2 = self.node_width/2,self.height-self.node_width/2

        node_id_counter = 0
        while len(self.nodes) < self.number_nodes:
            self.canvas.update()
            cor_x = random.randint(rand_range_x1,rand_range_x2)
            cor_y = random.randint(rand_range_y1,rand_range_y2)

            cor_x = max(self.node_width/2, cor_x)
            cor_x = min(self.width-self.node_width/2, cor_x)
            cor_y = max(self.node_width/2, cor_y)
            cor_y = min(self.height-self.node_width/2, cor_y)

            dists = [n.get_distance((cor_x,cor_y)) for n in self.nodes]
            if all(dist > self.node_min_distance for dist in dists) and any(dist < self.node_at_most_one_max_distance for dist in dists):
                self.add_node(cor_x,cor_y,node_id_counter)
                node_id_counter += 1
                rand_range_x1 = min(rand_range_x1,self.nodes[-1].cor_x-self.node_at_most_one_max_distance)
                rand_range_x2 = max(rand_range_x2,self.nodes[-1].cor_x+self.node_at_most_one_max_distance)
                rand_range_y1 = min(rand_range_y1,self.nodes[-1].cor_y-self.node_at_most_one_max_distance)
                rand_range_y2 = max(rand_range_y2,self.nodes[-1].cor_y+self.node_at_most_one_max_distance)
            elif len(self.nodes) == 0:
                self.add_node(self.width/2,self.height/2,node_id_counter)
                node_id_counter += 1
                rand_range_x1 = self.nodes[-1].cor_x-self.node_at_most_one_max_distance
                rand_range_x2 = self.nodes[-1].cor_x+self.node_at_most_one_max_distance
                rand_range_y1 = self.nodes[-1].cor_y-self.node_at_most_one_max_distance
                rand_range_y2 = self.nodes[-1].cor_y+self.node_at_most_one_max_distance

    def connect_nodes(self):
        self.edges = []
        for n1_i,n1 in enumerate(self.nodes):
            for n2_i in range(n1_i+1,len(self.nodes)):
                n2 = self.nodes[n2_i]
                dist = n1.get_distance((n2.cor_x,n2.cor_y))
                if dist <= self.node_at_most_one_max_distance:
                    new_edge = Edge(self.canvas, n1,n2)
                    self.edges.append(new_edge)

    def mouse_click_callback_right(self, event):
        for n in self.nodes:
            clickdist = n.get_distance((event.x,event.y))
            if clickdist < self.node_width/2:
                pass

    def mouse_click_callback_left(self, event):
        to_remove = []
        for n in self.nodes:
            clickdist = n.get_distance((event.x,event.y))
            if clickdist <= n.width/2:
                self.simulation.label_routing_table_string_var.set(n.routing_table.to_string())

    def medium_access(self, send_node,message,tx_range):
        send_node.colorise(fill="red")
        self.medium_transmission_buffer.append((send_node,message,tx_range))

    def update_medium_transmissions(self):
        for transmission in self.medium_transmission_buffer:
            send_node,message,tx_range = transmission
            for edge in send_node.edges:
                edge.colorise(fill="red")
            for node in self.nodes:
                distance = node.get_distance((send_node.cor_x,send_node.cor_y))
                if distance <= tx_range:
                    node.receive(message)
        self.medium_transmission_buffer = []

    def update_step(self):
        self.canvas.itemconfigure(self.time_step_text,text="timestep: {:>3}".format(self.time_step))

        if self.update_step_type == 0:
            for node in self.nodes:
                node.update_step()
            self.update_step_type = 1

        elif self.update_step_type == 1:
            self.update_medium_transmissions()
            for edge in self.edges:
                edge.update_step()
            self.time_step += 1
            self.update_step_type = 0



    def run(self):
        while True:
            loop_start_time = time.time()

            self.canvas.update()

            loop_end_time = time.time()
            sleep_time = max(0, (1/self.update_rate)-(loop_end_time-loop_start_time))

            time.sleep(sleep_time)



class Simulation(object):
    def __init__(self,width,height):
        self.width = width
        self.height = height

        self.root = tk.Tk()
        self.root.config(background = "white")

        self.panel_width = 400

        self.left_frame = tk.Frame(self.root,width=self.panel_width,height=self.height, bg="#F5F5F5")
        self.left_frame.grid(row=0,column=0,padx=10,pady=10)

        self.slider_num_nodes = tk.Scale(self.left_frame, from_=5, to=180, resolution=5, orient=tk.HORIZONTAL, length=160)
        self.slider_num_nodes.grid(row=0, column=0, padx=5, pady=5)

        self.button_generate_network = tk.Button(self.left_frame, text="Generate Network", bg="#00F0FF", width=20, font="Monospace", command=self.button_generate_network_callback)
        self.button_generate_network.grid(row=2, column=0, padx=5, pady=5)

        self.button_iteration_step = tk.Button(self.left_frame, text="Iteration Step", bg="#00F0FF", width=20, font="Monospace", command=self.button_iteration_step_callback)
        self.button_iteration_step.grid(row=3, column=0, padx=5, pady=5)

        self.label_routing_table_string_var = tk.StringVar()
        self.label_routing_table_string_var.set("##### Routing Table for #{:<3} ######\n|DestID|NextHop|Metric|SeqNo|InstT|".format(""))

        self.label_routing_table = tk.Label(self.left_frame, textvariable=self.label_routing_table_string_var, font="Monospace", bg="#F5F5F5")
        self.label_routing_table.grid(row=4, column=0, padx=5, pady=5)

        self.simulation_canvas = SimulationCanvas(self, self.width-self.panel_width,self.height)
        self.simulation_canvas.start()

        self.root.wm_title("Link Reversal Simulation")
        self.root.mainloop()

    def button_generate_network_callback(self):
        number_nodes = self.slider_num_nodes.get()
        self.simulation_canvas.initialise_network(number_nodes)

    def button_iteration_step_callback(self):
        self.simulation_canvas.update_step()


if __name__ == "__main__":

    simulation = Simulation(1500,800)
