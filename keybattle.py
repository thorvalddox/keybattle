from flask import Flask,session,render_template,url_for,redirect,jsonify
import json
from collections import OrderedDict
from queue import Queue
from itertools import product
import random

app = Flask(__name__)
app.debug = True
app.secret_key = "Em6vCLOSKe0EXvvIjyQvANeJC3yqk2zY60n0JNW0ySyYy7bQRPZKVTI3qBfdbLr8"

element_displ = "FWAELD+-OCTI!?SP"

class Element:
    all_ = {}
    all_list = []
    all_names = {}
    def __init__(self,sphere,nameP,effect=""):
        self.name = nameP.split(":")[0]
        self.dname = "<span title=\"{2}\"><font color=\"{1}\">{0}</font></span>".format(*nameP.split(":"))
        self.sphere = sphere
        self.effect = effect
        self.index = len(Element.all_list)
        self.key = element_displ[self.index]
        Element.all_list.append(self)
        Element.all_names[self.name] = self
        self.opposite = None
    def __repr__(self):
        return ("E<{}>".format(self.name))
    def issphere(self,other):
        return(self.sphere==other.sphere)
    def iscontra(self,other):
        return(self==other.opposite)
    @classmethod
    def create(cls,sphere,string1,string2):
        a,b = cls(sphere,*string1.split("=")),cls(sphere,*string2.split("="))
        a.opposite = b
        b.opposite = a
        return a,b
    @classmethod
    def load(cls,filename):
        sphere = ""
        lastentry = None
        with open(filename) as file:
            for f in file.readlines():
                if f.startswith("["):
                    sphere = f.strip()[1:-1]
                    cls.all_[sphere] = []
                elif lastentry is None:
                    lastentry = f.strip()
                else:
                    cls.all_[sphere].extend(cls.create(sphere,lastentry,f.strip()))
                    lastentry = None
    @classmethod
    def get_all(cls):
        for i in cls.all_.values():
            yield from i
    @classmethod
    def get_all_comb(cls):
        el = list(cls.get_all())
        for i,l in enumerate(el):
            for j in range(i,len(el)):
                if i==j:
                    continue
                m = el[j]
                if not l.issphere(m):
                    yield l,m

def elements_to_hash(*elements):
    return("_".join(e.name for e in sorted(elements,key=lambda x:x.index)))

def elements_from_hash(string):
    return tuple(Element.all_names[i] for i in string.split("_"))

class Selector:
    def __init__(self,dict_=()):
        self.value = dict(dict_)
    def __getitem__(self, item):
        return self.value.get(item,False)
    def __setitem__(self, key, value):
        self.value[key] = value

class Monster:
    all_ = {}
    allmonsters = {}
    def __init__(self,el1,el2):
        self.id = elements_to_hash(el1,el2)
        self.unid = hex(random.randrange(16**16))
        self.elements = sorted((el1,el2),key=lambda x:x.index)
        self.name = Monster.allmonsters[self.id].split("=")[0].lower()
        self.image = Monster.allmonsters[self.id].split("=")[1]
        self.selected = Selector()
        Monster.all_[self.unid] = self
    def display(self,selectable=True,amount=1):
        return render_template("battler.html",name=self.name,image=url_for('static', filename=self.image+".png"),
                               e1=self.elements[0].dname,e2=self.elements[1].dname,selected=self.selected[session["uid"]],
                               unid=self.unid,selectable=selectable,amount=amount)
    def display_compact(self,amount=1):
        return render_template("battler.html",name=self.name,
                               e1=self.elements[0].dname,e2=self.elements[1].dname,selected=self.selected[session["uid"]],
                               unid=self.unid,amount=amount,selectable=True)
    def destroycost(self,other,costvec):
        """if not any(a.issphere(b) for a,b in product(self.elements,other.elements)):
            return costvec[1]
        elif not any(a.iscontra(b) for a,b in product(self.elements,other.elements)):
            return costvec[2]
        else:
            return costvec[3]""" #old method
        if not any(a.iscontra(b) for a,b in product(self.elements,other.elements)):
            return costvec[1]
        elif sum(a.issphere(b) for a,b in product(self.elements,other.elements)) < 2:
            return costvec[2]
        else:
            return costvec[3]
    @classmethod
    def load_names(cls):
        cls.allmonsters = {elements_to_hash(*a):"<no name>=<no image>" for a in Element.get_all_comb()}
        cls.allmonsters.update(json.load(open("monsters.json")))
        json.dump(OrderedDict(sorted(cls.allmonsters.items(), key=lambda t: tuple(Element.all_names[x].index for x in t[0].split("_")))),
                  open("monsters.json","w"),indent=0)


def randommonster():
    elementhashlist = list((elements_to_hash(a,b),(a,b)) for a,b in product(list(Element.get_all()),repeat=2))
    monsterlist = [y for x,y in elementhashlist if (x in Monster.allmonsters) and not (Monster.allmonsters[x].startswith("<"))]
    print("possibilities:",len(monsterlist)//2,"/",len(Monster.allmonsters))
    m = random.choice(monsterlist)
    return Monster(*m)

class Player:
    # TODO save and load after sever reset
    all_ = {}
    waiting = []
    @classmethod
    def get(cls):
        if "uid" not in session or session["uid"] not in Player.all_:
            return cls()
        else:
            return Player.all_[session["uid"]]
    @classmethod
    def save_all(cls):
        with open("players.json","w") as fff:
            json.dump([i.save() for i in cls.all_.values()],fff,indent=3)
    @classmethod
    def load_all(cls):
        with open("players.json","r") as fff:
            for i in json.load(fff) :
                cls(i)
    def __init__(self,databank=...):
        if databank == ...:
            self.uid = hex(random.randrange(16**16))
            session["uid"] = self.uid
            self.monsters = Deck()
            self.deck = Deck()
            self.monsters.addrandom(10)
            self.cash = 100
        else:
            self.uid = databank["uid"]
            self.monsters = Deck.from_json(databank["monsters"])
            self.deck = Deck.from_json(databank["deck"])
            self.cash = databank["cash"]


        Player.all_[self.uid] = self
        self.name = "Player_" + self.uid[2:10]
        self.currentBattle = None

    def entergame(self):
        if not self.uid in Player.waiting:
            Player.waiting.append(self.uid)
        if len(Player.waiting) >= 2:
            p1 = Player.all_[Player.waiting.pop(0)]
            p2 = Player.all_[Player.waiting.pop(0)]
            Player_Battle(p1,Player_Battle(p2)).active = True
        Player.save_all()
    def startAIgame(self):
        Player_Battle(self,AI_battle()).active = True
        Player.save_all()

    #def display_all_Monsters(self,selectable=False):
    #    return self.monsters.display(selectable)

    def render_options(self):
        return {"money":self.cash,"monsters":self.monsters.display(True),"deck":self.deck.display(True),"uid":self.uid}
    def get_json(self):
        return self.render_options()
    def save(self):
        return {"name":self.name,
                "uid":self.uid,
                "monsters":self.monsters.to_json(),
                "deck":self.deck.to_json(),
                "cash": 100}


class Deck():
    def __init__(self):
        self.cards = []
    def add(self,el1,el2):
        self.cards.append(Monster(el1,el2))
        self.sort()
    def copy(self):
        s = type(self)()
        s.cards = self.cards.copy()
        return s
    def swap(self,other,monster):
        if monster in self.cards:
            self.cards.remove(monster)
            other.cards.append(monster)
            return monster
        elif monster in other.cards:
            other.cards.remove(monster)
            self.cards.append(monster)
            return monster
    def swap_selected(self,other,uid):
        for x in self.cards+other.cards:
            if x.selected[uid]:
                self.swap(other,x)
    def addrandom(self,amount=1):
        self.cards.extend(randommonster() for _ in range(amount))
        s = self.cards[-1]
        self.sort()
        return s
    def sort(self):
        self.cards.sort(key=lambda x:[e.index for e in x.elements])
    def __getitem__(self, item):
        return self.cards[item]
    def drawfrom(self,other,index=...):
        if index == ...:
            index = random.randrange(len(other.cards))
        self.cards.append(other.cards.pop(index))
        return self.cards[-1]
    def destroy(self,item):
        return self.cards.pop(item)
    def displaydict(self):
        hashlist = [x.id for x in self.cards]
        yieldedids = []
        self.compact = sorted(list(set(self.cards)),key=lambda x:[e.index for e in x.elements])
        for i in self.compact:
            if i.id not in yieldedids:
                yieldedids.append(i.id)
                yield (i,hashlist.count(i.id))
    def display_old(self,selectable):
        return '<table><tr><td>' + \
            doublejoin("</td></tr><tr><td>","</td><td>",[m.display(selectable,a) for m,a in self.displaydict()],8) + \
               "</td></tr></table>"
    def display(self,selectable):
        return '<div class=\"deck\"><table><tr><td class=\"deck\">' + \
                "</td><td class=\"deck\">".join(m.display(selectable,a) for m,a in self.displaydict()) + \
                "</td></tr></table></div>"
    def display_compact(self):
        return '<table><tr><td>' + \
            doublejoin("</td></tr><tr><td>","</td><td>",[m.display_compact(a) for m,a in self.displaydict()],8) + \
               "</td></tr></table>"
    def get_selection_count(self,playeruid):
        return sum(m.selected[playeruid] for m in self.cards)
    def get_selection_index(self,playeruid):
        return next((i for i,x in enumerate(self.cards) if x.selected[playeruid]), random.randrange(len(self.cards)))
    def get_selection_set(self,playeruid):
        return set(i for i,x in enumerate(self.cards) if x.selected[playeruid])
    def get_selection_unit(self,playeruid):
        return self[self.get_selection_index(playeruid)]
    @staticmethod
    def full_deselect(uid):
        for i in Monster.all_.values():
            i.selected[uid] = False
    def to_json(self):
        return [m.id for m in self.cards]
    @classmethod
    def from_json(cls,data):
        s = cls()
        s.cards = [Monster(*elements_from_hash(i)) for i in data]
        return s



def doublejoin(d1,d2,l,n):
    chunks = [d2.join(l[i:i+n]) for i in range(0, len(l), n)]
    return d1.join(chunks)

def chance(c):
    return random.random()*c < 1

def relpos(index,tpe,maxi,r,g,b):
    color = ",".join((str(r),str(g),str(b)))
    return """<svg>
                <rect width="20" height="20" style="fill:rgb(255,255,255);stroke-width:3;stroke:rgb({})" />
            </svg>""".format(color)*(maxi + index) + \
           open("static/icons/" + "world.svg;holy-grail.svg;star-swirl.svg;mailed-fist.svg".split(";")[tpe]).read()\
               .format("rgb(" + color + ")") + \
            """<svg>
                <rect width="20" height="20" style="fill:rgb(255,255,255);stroke-width:3;stroke:rgb({})" />
            </svg>""".format(color)*(maxi - index)

class Player_Battle:
    def __init__(self,master:Player,opponent=None):
        if opponent is not None:
            self.opponent = opponent
            opponent.opponent = self
        self.master = master
        self.name = self.master.name
        self.master.currentBattle = self
        self.table = Deck()
        self.hand = Deck()
        self.coins = 20
        self.log = []
        self.active = False
        self.deck = self.master.deck.copy()
        for _ in range(5):
            self.hand.drawfrom(self.deck)

    def has_element(self,el):
        return any(el in m.elements for m in self.table)
    def new_monster(self,index):
        s = self.table.drawfrom(self.hand,index)
        self.hand.drawfrom(self.deck)
        self.add_to_log("{} spawned {}".format(self.name,s.name),"blue")
    def costs(self):
        s = lambda x:self.has_element(Element.all_names[x])
        t = lambda x:self.opponent.has_element(Element.all_names[x])
        return 10 - 2*s("life") + 2*t("order"), 12 - 3*s("fire") + 3*t("earth"), \
               8 - 3*s("air") + 3*t("light") , 4 - 3*s("force") + 3*t("matter")
    def end_turn(self):
        Deck.full_deselect(self.master.uid)
        self.add_to_log("{} ended his turn".format(self.name))
        if not self.active:
            return
        if self.check_won():
            self.active = False
            return redirect("/battle/end/")
        self.opponent.active = True
        self.active = False
        self.opponent.start_turn()
        return ('',204)
    def start_turn(self):
        s = lambda x:self.has_element(Element.all_names[x])
        t = lambda x:self.opponent.has_element(Element.all_names[x])
        steal = chance(2)*s("darkness")
        self.coins += 4 + s("time") + chance(2)*s("speed")*2 + chance(4)*s("chaos")*4 + steal
        self.opponent.coins -= steal
    def onkill(self):
        s = lambda x:self.has_element(Element.all_names[x])
        t = lambda x:self.opponent.has_element(Element.all_names[x])
        self.coins += s("death")*2 + s("water")
    def ondead(self):
        s = lambda x:self.has_element(Element.all_names[x])
        t = lambda x:self.opponent.has_element(Element.all_names[x])
        self.coins += s("infinite") + s("water") + 3*s("phantom")
        self.opponent.coins -= s("infinite")
    def check_won(self):
        for i in Element.all_.values():
            if all(self.has_element(j) for j in i) and not any(self.opponent.has_element(j) for j in i):
                self.finish(True)
                self.opponent.finish(False)
                return True
        return False
    def finish(self,won):
        self.master.cash += 1000*won
        self.deck.cards.extend(self.table.cards)
        self.deck.cards.extend(self.hand.cards)
        self.master.currentBattle = None

    def redraw(self):
        if not self.active:
            return ('',204)
        if self.coins >= 1:
            self.coins -= 1
            for _ in range(5):
                self.deck.drawfrom(self.hand)
            for _ in range(5):
                self.hand.drawfrom(self.deck)
            self.end_turn()
        return ('',204)
    def handle(self):
        if not self.active:
            return ('',204)
        bcost = self.costs()[0]
        if self.coins >= bcost and self.hand.get_selection_count(self.master.uid):
            self.new_monster(self.hand.get_selection_index(self.master.uid))
            self.coins -= bcost
            return self.end_turn()

        if self.table.get_selection_count(self.master.uid) and self.opponent.table.get_selection_count(self.master.uid):
            attkr = self.table.get_selection_unit(self.master.uid)
            target = self.opponent.table.get_selection_unit(self.master.uid)
            kcost = attkr.destroycost(target,self.costs())
            if self.coins >= kcost:
                self.coins -= kcost
                self.onkill()
                self.opponent.ondead()
                self.opponent.kill_monster(target)
                self.add_to_log("{} killed {} with {}".format(self.name,attkr.name,target.name),"red")
                del target
            Deck.full_deselect(self.master.uid)
        return ('',204)

    def kill_monster(self,target):
        self.table.swap(self.deck,target)


    def aspects(self,other):
        keys = Element.all_.keys()
        color = {"classic":(0,127,0),"spiritual":(0,127,255),"cosmic":(0,0,127),"intern":(255,0,0)}
        return {k:relpos(sum(self.has_element(i) - other.has_element(i) for i in Element.all_[k]),
                   Element.all_[k][0].index//4,4,*color[k]) for k in keys}

    def display_table(self):
        return self.table.display(True)
        #return '<table><tr><td>' + "</td><td>".join(m.display() for m in self.table) + "</td></tr></table>"

    def datadisp(self):
        info = {"monsters":self.table.display(True),
                "coins":self.coins,"costs":self.costs(),"active":self.active,
                "log":self.show_log(8)}
        try:
            info["hand"] = self.hand.display(True)
        except AttributeError:
            info["hand"] = "N/A"
        info.update(self.aspects(self.opponent))
        return(info)
    def display_as_enemy(self):
        return render_template("render_as_enemy.html",**self.datadisp())
    def display_as_player(self):

        return render_template("render_as_player.html",**self.datadisp())
    def get_json(self):
        return {"player":self.display_as_player(),"enemy":self.opponent.display_as_enemy()}

    def add_to_log(self,text,color="black"):
        self.log.append("<font color=\"{}\">{}</font>".format(color,text))
        self.opponent.log.append("<font color=\"{}\">{}</font>".format(color,text))
    def show_log(self,lines):
        return "<br/>".join(self.log[-lines:])


class AI_battle(Player_Battle):
    def __init__(self,opponent=None):
        if opponent is not None:
            self.opponent = opponent
            opponent.opponent = self
        self.table = Deck()
        self.coins = 20
        self.active = False
        self.uid = "AI" + hex(random.randrange(16**16))
        self.name = "computer"
        self.log = []
    def new_monster(self,index=...):
        s = self.table.addrandom(1)
        self.add_to_log("{} spawned {}".format(self.name,s.name),"blue")
    def start_turn(self):
        s = lambda x:self.has_element(Element.all_names[x])
        t = lambda x:self.opponent.has_element(Element.all_names[x])
        steal = chance(2)*s("darkness")
        self.coins += 2 + s("time") + chance(2)*s("speed")*2 + chance(4)*s("chaos")*4 + steal
        self.opponent.coins -= steal
        self.handle_all()
    def handle_all(self):
        if not self.active:
            return
        bcost = self.costs()[0]
        if len(self.table.cards) and len(self.opponent.table.cards):
            attkr = self.table.get_selection_unit(self.uid)
            target = self.opponent.table.get_selection_unit(self.uid)
            kcost = attkr.destroycost(target,self.costs())
            if self.coins >= kcost+bcost or bcost > self.coins >= kcost or (self.coins >= kcost and len(self.table.cards) >= 5):
                self.coins -= kcost
                self.onkill()
                self.opponent.ondead()
                self.opponent.kill_monster(target)
                self.add_to_log("{} killed {} with {}".format(self.name,attkr.name,target.name),"red")
                del target

        if self.coins >= bcost:
            self.new_monster()
            self.coins -= bcost
        Deck.full_deselect(self.uid)
        self.end_turn()
    def end_turn(self):
        Deck.full_deselect(self.uid)
        self.add_to_log("{} ended his turn".format(self.name))
        if not self.active:
            return
        if self.check_won():
            self.active = False
            return
        self.opponent.active = True
        self.active = False
        self.opponent.start_turn()
    def finish(self,won):
        pass
    def kill_monster(self,target):
        self.table.cards.remove(target)

@app.route('/')
def main():
    player = Player.get()
    if player.currentBattle is not None:
        return redirect("/battle/")
    return render_template("mainscreen.html",**player.render_options())

@app.route('/addmonster/')
def addnewmonster():
    player = Player.get()
    player.monsters.addrandom(10)
    Player.save_all()
    return ('',204)

@app.route('/battle/')
def battle():
    player = Player.get()
    if player.currentBattle is None:
        player.entergame()
        return render_template("waiting.html")
    return render_template("combat.html")

@app.route('/battle/AI/')
def battle_AI():
    player = Player.get()
    if player.currentBattle is None:
        player.startAIgame()
    return redirect("/battle/")

@app.route('/battle/leaveQueue/')
def leaveQueue():
    player = Player.get()
    if player.currentBattle is None:
        if player.uid in Player.waiting:
            Player.waiting.remove(player.uid)
    return redirect("/")

@app.route('/battle/endturn/')
def End_turn():
    player = Player.get()
    if player.currentBattle is not None:
        player.currentBattle.end_turn()
    return ('', 204)


@app.route("/battle/end/")
def end_battle():
    return render_template("battle_end.html")


@app.route('/battle/redraw/')
def battle_redraw():
    player = Player.get()
    if player.currentBattle is not None:
        return player.currentBattle.redraw()
    return ('', 204)

@app.route("/get/data/battle/")
def get_battle_data():
    player = Player.get()
    if player.currentBattle is None:
        return redirect("/battle/end/")
    else:
        return jsonify(player.currentBattle.get_json())

@app.route("/get/data/main/")
def get_main_data():
    player = Player.get()
    return jsonify(player.get_json())

@app.route("/select/monster/<unid>/")
def select_monster(unid):
    player = Player.get()
    Monster.all_[unid].selected[player.uid] = not Monster.all_[unid].selected[player.uid]
    if player.currentBattle is not None:
        return player.currentBattle.handle()
    else:
        player.deck.swap_selected(player.monsters,player.uid)
        player.deck.full_deselect(player.uid)
        player.monsters.full_deselect(player.uid)
        Player.save_all()
    return ('',204)

if __name__ == '__main__':
    Element.load("elements.txt")
    Monster.load_names()
    print(repr(Element.all_))
    Player.load_all()
    app.run()
