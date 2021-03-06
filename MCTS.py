
import numpy as np
from copy import deepcopy
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
from datetime import datetime
import random
import time
import json



class Node(object):
    def __init__(self, state, remain_rooms, ini_Q, info, next_positions):
        """

        :param state: the state matrix of this node
        :param remain_rooms: the remaining_rooms to put into this state
        :param ini_Q: initial Q value
        :param info: (type, value)
                    if type is 'R', value is None
                    if type is 'X', value is selected end_x
                    if type is 'Y', value is (y,x)
        :param next_positions: ( (pos_y, pos_x), (original_y_intervals, original_x_intervals) )
        """
        self.state = state
        self.row, self.col = self.state.shape
        self.remain_rooms = remain_rooms
        self.ini_Q = ini_Q
        self.type = info[0]
        self.value = info[1]
        (self.pos_y, self.pos_x), (self.ori_y_intervals, self.ori_x_intervals) = next_positions

        self.N = 0
        self.Q = 1
        self.W = 0
        self.expanded = False

    def expand(self):
        self.expanded = True
        if self.type in ['X','Y']:
            self.terminal = False
            self.fetch_children()
        else:
            assert self.type=='R', 'unknown node type'
            if len(self.remain_rooms) == 0:
                self.terminal = True
                self.complete()
            else:
                self.terminal = False
                self.fetch_children()

        return

    def find_next_position(self):
        for y in range(0, self.row):
            for x in range(0, self.col):
                if self.state[y][x] == 0:
                    return y,x

        raise TypeError('can not find next empty space')


    def find_x_intervals(self):
        intervals = [self.pos_x]

        # get two end intervals
        for x in range(self.pos_x, self.col):
            if self.state[self.pos_y][x] != 0:
                intervals.append(x)
                break
        if len(intervals) == 1:
            intervals.append(self.col)
        else:
            assert len(intervals) == 2, 'x first interval check should be 2'

        # get upper medium intervals
        if self.pos_y != 0:  # not upper border
            sign = self.state[self.pos_y - 1][self.pos_x]
            for x in range(self.pos_x, intervals[1]):
                if sign != self.state[self.pos_y - 1][x]:
                    sign = self.state[self.pos_y - 1][x]
                    intervals.insert(-1, x)

        return intervals

    def find_y_intervals(self):
        intervals = set()
        intervals.add(self.pos_y)
        intervals.add(self.row)
        edges= []
        for x in range(0, self.col):
            for y in range(0, self.row):
                if self.state[y][x]==0:
                    edges.append(y)
                    break
                if y == self.row - 1:
                    edges.append(self.row)

        edges=np.array(edges)
        assert len(edges) == self.col, 'edge size not match self.col'
        assert self.pos_x == edges.argmin(), 'minimum position is not pos_x?'
        assert self.pos_y == np.min(edges), 'minimum position is not pos_y?'
        max_left = self.pos_y
        for i in range(self.pos_x,-1,-1):
            if edges[i] > max_left:
                max_left = edges[i]
                intervals.add(max_left)
        max_right = self.pos_y
        for i in range(self.pos_x, self.col):
            if edges[i] > max_right:
                max_right = edges[i]
                intervals.add(max_right)

        intervals = list(intervals)
        intervals.sort()
        return intervals


    def fetch_children(self):
        self.children = []

        if self.type == 'R':
            self.pos_y, self.pos_x = self.find_next_position()
            self.ori_x_intervals = self.find_x_intervals()
            self.ori_y_intervals = self.find_y_intervals()
            xs, x_states = self.choose_x()  # get all possible x states
            for x, x_state in zip(xs, x_states):
                child = Node(x_state,self.remain_rooms,self.ini_Q, ('X',x), ((self.pos_y, self.pos_x),(self.ori_y_intervals,self.ori_x_intervals)))
                self.children.append(child)

        elif self.type == 'X':
            ys, y_states = self.choose_y()
            for y, y_state in zip(ys,y_states):
                child = Node( y_state, self.remain_rooms, self.ini_Q, ('Y',(y,self.value)), ((self.pos_y, self.pos_x), (self.ori_y_intervals,self.ori_x_intervals)) )
                self.children.append(child)

        elif self.type == 'Y':
            for id in self.remain_rooms:
                remain_rooms = [n for n in self.remain_rooms if n!=id]
                new_state = self.create_room(id)
                child = Node(new_state, remain_rooms, self.ini_Q, ('R', None), ((None,None),(None,None)) )
                self.children.append(child)
            #id = self.remain_rooms[0]
            #remain_rooms = self.remain_rooms[1:]
            #new_state = self.create_room(id)
            #child = Node(new_state, remain_rooms, self.ini_Q, ('R', None), ((None,None),(None,None)) )
            #self.children.append(child)

        else:
            raise TypeError('unknown node type')

        return


    def choose_x(self): # checked ok
        xs = []
        states = []

        # create states
        for i in range(0, len(self.ori_x_intervals)-1):
            start = self.ori_x_intervals[i]
            end = self.ori_x_intervals[i+1]
            # all
            xs.append( end )
            states.append( deepcopy(self.state) )

            # half
            if start == end-1:
                new_state = np.insert( self.state, start+1 , self.state[:,start] , axis=1) # No problem, only changes interval of this state
            else:
                assert end-1 > start, 'end-1: {} should > start: {}'.format(end-1 , start)
                new_state = deepcopy(self.state)
            xs.append(start+1)
            states.append(new_state)

        return xs, states

    def choose_y(self):
        ys = []
        states = []

        # create states
        for i in range(0, len(self.ori_y_intervals) -1):
            start = self.ori_y_intervals[i]
            end = self.ori_y_intervals[i+1]
            # all
            if self.value==self.col and end==self.row:
                pass
            else:
                ys.append(end)
                states.append( deepcopy(self.state) )

            # half
            if start==end-1:
                new_state = np.insert(self.state, start+1, self.state[start,:], axis=0)
            else:
                assert end-1 > start, 'y end-1 should > y start'
                new_state=deepcopy(self.state)
            ys.append( start+1 )
            states.append(new_state)

        return ys,states

    def create_room(self,id):

        end_y, end_x = self.value
        new_state = deepcopy(self.state)
        for y in range(self.pos_y, end_y):
            for x in range(self.pos_x, end_x):
                assert new_state[y][x] == 0, 'create new room, but not empty'
                new_state[y][x]=id

        return new_state

    def complete(self):
        # complete horizontal
        for x in range(0, self.col-1):
            start = None
            for y in range(self.row-1, -1, -1):
                if self.state[y][x] != 0 and start==None:
                    start = y
                    value = self.state[y][x]

                if start != None:
                    if value != self.state[y][x]:
                        end = y
                        if (self.state[end+1:start+1,x+1]==0).all():
                            self.state[end + 1:start + 1,x+1] = value

                        break
                if y==0:
                    assert start!= None, 'find empty column which is not the last column'
                    assert value == self.state[y][x], 'should break'
                    if (self.state[0:start+1, x+1]==0).all():
                        self.state[0:start+1, x+1] = value

        # complete vertically
        for x in range(0, self.col):
            for y in range(0, self.row):
                if self.state[y][x] == 0:
                    value = self.state[y-1][x]
                    assert value!=0, 'vertical fill value=0, state{}'.format(self.state)
                    self.state[y:self.row, x] = value
                    break

        assert (self.state[:]!=0).all(), 'still have empty space'

        return




class simulation(object):
    def __init__(self,rootnode,Cons,sim_rand, avg):
        self.currentnode = rootnode
        self.Cons = Cons
        self.path = [self.currentnode]

        self.sim_rand = sim_rand
        self.avg = avg

    def run(self):

        while True:
            if not self.currentnode.expanded:
                self.currentnode.expand()

            if self.currentnode.terminal:
                all_reward = total_return(self.Cons, self.currentnode.state, self.currentnode.ini_Q)
                backup(self.path,all_reward, self.avg)
                return
            else:
                self.currentnode = self.select(self.currentnode)
                self.path.append(self.currentnode)



    def select(self,node):
        sum_N = np.sum([child.N for child in node.children])

        if self.sim_rand:
            np.random.shuffle(node.children)
            #maxval = max([(nd.Q + (np.sqrt(sum_N) / (1 + nd.N))) for nd in node.children])
            #max_nodes = [nd for nd in node.children if (nd.Q + (np.sqrt(sum_N) / (1 + nd.N))) == maxval]
            #sel_node = random.choice(max_nodes)
        sel_node = max(node.children, key=lambda nd: ( nd.Q + EXPLORE_RATE * (  np.sqrt(sum_N)  / (1 + nd.N) ) ) )
        return sel_node







class MCTS(object):
    def __init__(self, Cons, num_search, caseid, sim_rand=False, play_rand=False, avg=False):
        """

        :param Cons: numpy constraints array where -1 means not to be neighbor, +1 means to be neighbor and 0 means no constraints.
        [[0, 1,-1],
         [0, 0, 1],
         [0, 0, 0]]

         all_rooms = [1,2,3,...]

         state =
         [
         [4,4,3,3]
         [4,4,1,1]
         [2,2,2,0]
         [0,0,0,0]
         ]
        """
        assert Cons.shape[0]== Cons.shape[1], 'constraints matrix should have the same dimension on col and row'
        self.Cons = Cons
        self.num_search = num_search
        self.all_rooms = [id for id in range(1, Cons.shape[0]+1)]
        self.current_node = Node(np.array([[0]]), self.all_rooms, np.count_nonzero(self.Cons), ('R', None), ((None,None),(None,None)) )
        self.real_path = [self.current_node]

        self.sim_rand = sim_rand
        self.play_rand = play_rand
        self.case_id = caseid
        self.avg =avg

    def play(self):
        self.records = [[0,0,0]]
        self.i=0
        while True:
            sign = self.play_one_move(self.current_node)
            if sign:
                return self.records
            if self.current_node.terminal:
                #backup(self.real_path, self.current_node.Q)
                self.i += 1

                record = [ time.time()-START_TIME , self.i, self.current_node.Q]
                print('time: {}, iter: {}, results: {}'.format(record[0],record[1],record[2]) )
                self.records.append(record)

                #vis
                states_path = self.real_path
                vis_stats = [node.state for node in states_path if node.type == 'R']
                vis_stats.pop(0)
                vis = Visualisation(self.all_rooms, vis_stats, self.Cons, self.current_node.Q)
                vis.vis_static('{}search_rate_{}_iter_{}.png'.format(self.num_search, 2, self.i))

                if record[0]>3000:
                    print('Endless')
                    return self.records
                else:
                    self.current_node = self.real_path[0]
                    self.real_path = [self.current_node]

    def play_one_move(self, startnode):
        for i in range(0,self.num_search):
            sl = simulation(startnode, self.Cons, self.sim_rand, self.avg)
            sl.run()
            #backup(self.real_path, sl.currentnode.Q)
            if sl.currentnode.Q == 1:

                record = [time.time()-START_TIME, self.i+1 , sl.currentnode.Q]
                print('time:{}, iter:{}, END_{}'.format(record[0],record[1], record[2]))
                self.records.append(record)

                states_path = self.real_path + sl.path[1:]
                vis_stats = [node.state for node in states_path if node.type == 'R']
                vis_stats.pop(0)
                vis = Visualisation( self.all_rooms, vis_stats, self.Cons, sl.currentnode.Q )
                vis.vis_static('{}search_{}simrand_{}playrand_{}avg_{}caseid_{}exp.png'.format(self.num_search,self.sim_rand,self.play_rand, self.avg, self.case_id,EXPLORE_RATE))
                return True

        if self.play_rand:
            np.random.shuffle(startnode.children)
            #maxval = max([nd.Q for nd in startnode.children])
            #maxelements = [nd for nd in startnode.children if nd.Q == maxval]
            #sel_node = random.choice(maxelements)


        sel_node = max(startnode.children, key=lambda nd:nd.Q)
        #sum_N = np.sum([child.N for child in startnode.children])
        #sel_node = max(startnode.children, key=lambda nd: (nd.Q + EXPLORE_RATE * (np.sqrt(sum_N) / (1 + nd.N))))
        self.current_node = sel_node
        self.real_path.append(self.current_node)
        return False



def backup(path,all_reward,avg = False):
    """
    backup reward to all the nodes in the path
    :param path:
    :param all_reward:
    :return:
    """
    if avg:
        for node in path:
            node.N += 1
            node.W += all_reward
            node.Q = node.W/node.N
    else:
        for node in path:
            node.N += 1
            #node.W += all_reward
            #node.Q = node.W/node.N
            if node.N == 1:
                node.Q = all_reward
            else:
                if all_reward > node.Q:
                    node.Q = all_reward

    return


def total_return(cons,state, ini_Q):
    """
    compare the constraint and state to calculate total return
    :param cons:
    [
    [0, 1, 0, -1],
    [0, 0, 0, 1],
    [0, 0, 0, -1],
    [0, 0, 0, 0]
    ]
    1 means must be connected
    -1 means must be disconnected
    0 means whatever
    :param state:
    :return:
    """
    connect = np.full(cons.shape, -1)

    # horizontal connectivity
    for row in state:
        pre_id = row[0]
        for id in row:
            if id != pre_id:
                connect[id - 1][pre_id - 1] = 1
                connect[pre_id - 1][id - 1] = 1
                pre_id = id

    # vertical connectivity
    for row in state.T:
        pre_id = row[0]
        for id in row:
            if id != pre_id:
                connect[id - 1][pre_id - 1] = 1
                connect[pre_id - 1][id - 1] = 1
                pre_id = id

    # calculate return
    reward = np.sum(cons * connect)
    # scale to between -1 and 1
    reward = reward / ini_Q
    return reward


class Visualisation(object):
    def __init__(self, room_ids, states_path, consMat, Q):
        """
        visualise a sequence of floorplan states
        :param room_ids: total room list [1,2,3,4,5,...]
        :param states_path: a sequence of floorplan states
        :param consMat: constraint matrix
        :param Q: final score
        """
        self.room_ids = room_ids
        self.states_path = states_path
        self.consMat = consMat
        self.Q = Q
        self.num_of_frame = len(states_path) + 1

        self.color_map = [(1.,1.,1.)]
        for n in self.room_ids:
            self.color_map.append(tuple(np.random.rand(3)))


    def vis_static(self,figname):
        self.size = int( np.ceil(  np.sqrt( self.num_of_frame ) )  )
        self.fig = plt.figure(figsize=(9,9))
        self.fig.suptitle('Result score: {}'.format(self.Q))

        # plot state
        for i,state in enumerate(self.states_path):
            ax = self.fig.add_subplot(self.size,self.size, i+1)
            self.show_per_image(ax, state, i+1)


        # plot constraint
        ax = self.fig.add_subplot(self.size,self.size, self.size*self.size)
        self.show_constraint(ax)


        self.fig.savefig(figname)

    def show_per_image(self,ax,state,i):
        image = []
        for row in state:
            img_row = []
            for rid in row:
                img_row.append( self.color_map[rid] )
            image.append(img_row)


        ax.imshow(np.array(image))
        ax.tick_params(bottom=False, left=False, labelbottom=False,labelleft=False)
        ax.set_title(i)

        # text annoation
        for y in range(state.shape[0]):
            for x in range(state.shape[1]):
                ax.text(x, y, state[y, x],
                        ha="center", va="center", color="w")

        return

    def show_constraint(self,ax):

        ax.imshow(self.consMat, cmap='Greys')
        ax.tick_params(bottom=False, labelbottom=False, top=True, labeltop=True)
        ax.set_xticks(np.arange(len(self.room_ids)))
        ax.set_yticks(np.arange(len(self.room_ids)))
        ax.set_xticklabels(range(1, len(self.room_ids) + 1))
        ax.set_yticklabels(range(1, len(self.room_ids) + 1))
        ax.set_xlabel('Constraint Matrix')
        ax.set_xticks(np.arange(self.consMat.shape[1] + 1) - .5, minor=True)
        ax.set_yticks(np.arange(self.consMat.shape[0] + 1) - .5, minor=True)
        ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
        ax.tick_params(which="minor", bottom=False, left=False)


if __name__=='__main__':

    # case 1 constraints without nonadjacency requirements

    Cons1 = np.array(
        [
            [0,1,1,1,1,0,0,0,0],
            [0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,1],
            [0,0,0,0,0,1,0,0,0],
            [0,0,0,0,0,1,1,1,1],
            [0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,1,0],
            [0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0]
        ]
    )



    # case 1 constraints with nonadjacency requirements
    Cons1_non = np.array(
        [
            [0,1,1,1,1,-1,-1,-1,-1],
            [0,0,-1,0,-1,-1,-1,-1,-1],
            [0,0,0,-1,0,-1,-1,-1,1],
            [0,0,0,0,-1,1,-1,-1,-1],
            [0,0,0,0,0,1,1,1,1],
            [0,0,0,0,0,0,0,-1,-1],
            [0,0,0,0,0,0,0,1,-1],
            [0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0]
        ]
    )


    # case 2 constraints with nonadajency requirements
    Cons2_non = np.array(
        [
            [0,1,1,-1,-1,-1, 1,-1,-1,-1,-1,-1],
            [0,0,1, 1, 1,-1,-1,-1,-1,-1,-1,-1],
            [0,0,0, 1,-1,-1, 1, 1, 1,-1,-1,-1],
            [0,0,0, 0, 1, 1,-1,-1, 1,-1,-1,-1],
            [0,0,0, 0, 0, 1,-1,-1,-1,-1,-1,-1],
            [0,0,0, 0, 0, 0,-1,-1, 1,-1,-1,-1],
            [0,0,0, 0, 0, 0, 0, 1,-1,-1,-1, 1],
            [0,0,0, 0, 0, 0, 0, 0, 1, 1,-1, 1],
            [0,0,0, 0, 0, 0, 0, 0, 0, 1, 1,-1],
            [0,0,0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            [0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [0,0,0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        ]
    )

    # case 2 constraints without non adjacency
    Cons2 = Cons2_non==1
    Cons2 = Cons2.astype(int)



    # experiment setting for case 1
    #EXPLORE_RATE = 1.0
    #case = 1
    #configs = [ {'n_search':250, 'cons':Cons1, 'color':'r', 'sim_rand':False, 'play_rand':True, 'case':'1', 'label':'without_nonadj'},
    #            {'n_search':1000, 'cons':Cons1_non, 'color':'b', 'sim_rand':False, 'play_rand':True, 'case':'1non', 'label':'with_nonadj'}
    #            ]
    #options = [
    #    {'avg':False, 'line_style':'.-', 'algorithm':'our'},
    #    {'avg': True, 'line_style': '<:', 'algorithm':'on-policy'},
    #]

    # experiment setting for case 2
    #rates_set = [1.0,2.0]
    #search_set = [1000,2000,3000,5000]
    #case = 2
    #configs = [{'cons': Cons2, 'color': 'r', 'sim_rand': False, 'play_rand': False, 'case': '2',
    #            'label': 'without_nonadj'},
    #           {'cons': Cons2_non, 'color': 'b', 'sim_rand': False, 'play_rand': False, 'case': '2non',
    #            'label': 'with_nonadj'}
    #           ]
    #options = [
    #    {'avg': False, 'line_style': '.-', 'algorithm': 'our'},
    #    {'avg': True, 'line_style': '<:', 'algorithm': 'on-policy'},
    #]

    # experiment setting for reviewer
    ConsR1 = np.array(
        [
            [0, 1, 1, 1, 0, 0, 0],
            [0, 0, 1, 1, 0, 1, 1],
            [0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 0, 1, 1, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0],
        ]
    )

    ConsR2 = np.array(
        [
            [0, 1, 1, -1, -1, -1, -1, -1],
            [0, 0, -1, 1, -1, -1, -1, -1],
            [0, 0, 0,  1,  1, -1, -1, -1],
            [0, 0, 0,  0, -1,  1, -1, -1],
            [0, 0, 0,  0,  0,  1,  1, -1],
            [0, 0, 0,  0,  0,  0,  1,  1],
            [0, 0, 0,  0,  0,  0,  0, -1],
            [0, 0, 0,  0,  0,  0,  0,  0]
        ]
    )

    ConsR3 = np.array(
        [
            [0, 1, 0, 1, 0, 1],
            [0, 0, 1, 0, 0, 1],
            [0, 0, 0, 1, 0, 1],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0],
        ]
    )

    ConsR4 = np.array(
        [
            [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
    )

    ConsR5 = np.array(
        [
            [0, 1, -1, -1, -1],
            [0, 0,  1, -1,  1],
            [0, 0,  0,  1,  1],
            [0, 0,  0,  0, -1],
            [0, 0,  0,  0,  0]
        ]
    )

    ConsR6 = np.array(
        [
            [0, 1, 1, -1, -1, -1, -1],
            [0, 0, 1, -1, -1, -1, -1],
            [0, 0, 0,  1, -1, -1, -1],
            [0, 0, 0,  0,  1,  1, -1],
            [0, 0, 0,  0,  0,  1,  1],
            [0, 0, 0,  0,  0,  0,  1],
            [0, 0, 0,  0,  0,  0,  0],
        ]
    )

    rates_set = [2.0]
    search_set = [5000]
    case = 'R1'
    configs = [{'cons': ConsR6, 'color': 'r', 'sim_rand': False, 'play_rand': False, 'case': 'R1',
                'label': 'without_nonadj'},
               ]
    options = [
        {'avg': False, 'line_style': '.-', 'algorithm': 'our'},
        {'avg': True, 'line_style': '<:', 'algorithm': 'on-policy'},
    ]


    # run and plot
    for EXPLORE_RATE in rates_set:
        for n_search in search_set:

            fig, ax = plt.subplots()

            for config in configs:
                for option in options:
                    print('---------')
                    print('explore rate:', EXPLORE_RATE)
                    print('n_search:', n_search )
                    print('config', config)
                    print('option', option)
                    Design = MCTS(config['cons'], n_search, caseid=config['case'], sim_rand=config['sim_rand'],play_rand=config['play_rand'], avg=option['avg'],)
                    START_TIME = time.time()
                    records = Design.play()
                    x = [record[0] for record in records]
                    y = [record[2] for record in records]
                    with open('{}search_{}simrand_{}playrand_{}avg_{}caseid_{}exp.json'.format(n_search,config['sim_rand'],config['play_rand'],option['avg'], config['case'],EXPLORE_RATE),'w') as f:
                        json.dump(records,f)
                    ax.plot(x,y,option['line_style'], label='{}_N={}_{}'.format(option['algorithm'], n_search, config['label']), color=config['color'])


            ax.legend()
            ax.set_xlabel('time (s)')
            ax.set_ylabel('Reward at each replay')
            fig.savefig('all_records_{}caseid_{}explor_{}search.png'.format(case,EXPLORE_RATE,n_search))

