import sqlite3
import numpy as np
import scipy.optimize
import sympy
from flask import g
from .database import get_db



def composite_get_mats(typeid, lookup, con, blocks=True):
    c = con.cursor()
    mats = np.zeros(len(lookup))
    # fuel blocks first step from DB

    outcome_quantity = c.execute("""SELECT product_quantity 
                                 from blueprints where product_typeID=? AND id != 45732;""", [typeid]).fetchone()[0]

    materials = c.execute("""SELECT material_id, material_quantity, group_id, name from blueprints b0
                                INNER JOIN blueprint_materials bm on b0.id = bm.blueprint_id
                                INNER JOIN typeIDs tID on tID.id = bm.material_id
                            WHERE b0.product_typeID==? AND b0.id != 45732;""", [typeid])

    for m in materials:
        # base case for fuel block and moon mats
        if not blocks and m[2] == 1136:
            # skipp fuel blocks
            continue

        if m[2] == 1136 or m[2] == 427:
            mats[lookup[m[0]]] += m[1]

        # scale by the amount needed and than add to the total
        else:
            (quantity, rec_mats) = composite_get_mats(m[0], lookup, con, blocks)
            scale = m[1] / quantity
            mats += rec_mats * scale

    return outcome_quantity, mats


def get_prices(typeids, conn, buy=False):
    c = conn.cursor()
    prices = []

    if buy:
        for t in typeids:
            prices.append(c.execute("SELECT buy FROM prices WHERE typeID==?", [t]).fetchone()[0] / 1000000)
    else:
        for t in typeids:
            prices.append(c.execute("SELECT sell FROM prices WHERE typeID==?", [t]).fetchone()[0] / 1000000)

    return prices


def get_optimizer():
    if 'optimizer' not in  g:
        g.optimizer = CompositeOptimizer(get_db())

    return g.optimizer



class CompositeOptimizer:
    def __init__(self, conn: sqlite3.Connection):
        c = conn.cursor()

        # all composite reactions
        composite = c.execute("""SELECT typeIDs.id, name, b.id, b.product_quantity from typeIDs
                            INNER JOIN blueprints b on typeIDs.id = b.product_typeID
                            WHERE group_id == 429;""").fetchall()

        self.lookup = {}
        for (i, x) in enumerate(c.execute("SELECT id FROM typeIDs WHERE group_id == 427 OR group_id == 1136;")):
            self.lookup[x[0]] = i

        self.lookup_no_blocks = {}
        for (i, x) in enumerate(c.execute("SELECT id FROM typeIDs WHERE group_id == 427;")):
            self.lookup_no_blocks[x[0]] = i

        self.lookup_product = {}
        for (i, x) in enumerate(c.execute("SELECT id FROM typeIDs WHERE group_id == 429 ")):
            self.lookup_product[x[0]] = i

        self.mat_dict = {}
        for c in composite:
            self.mat_dict[c[0]] = composite_get_mats(c[0], self.lookup, conn)

        self.mat_dict_no_blocks = {}
        for c in composite:
            self.mat_dict_no_blocks[c[0]] = composite_get_mats(c[0], self.lookup_no_blocks, conn, blocks=False)

        mask = np.ones((len(self.lookup),))
        mask[0] = 0
        mask[1] = 0
        mask[2] = 0
        mask[3] = 0

        # Ax = anzahl an input materiel (x vector der runs)
        self.A_Materials = np.matrix([ar[1] for (_, ar) in self.mat_dict.items()])
        self.A_Materials_mask_blocks = np.diag(mask).dot(self.A_Materials.T)
        self.A_Materials_no_blocks = np.matrix([ar[1] for (_, ar) in self.mat_dict_no_blocks.items()])

        # Ax = anzahl an produkten (x vector der runs)
        self.A_Products = np.diag([ar[0] for (_, ar) in self.mat_dict.items()])

        # skalierung um den ISK preis
        self.A_Input_Prices = np.diag(get_prices([i for i in self.lookup], conn))
        self.A_Materials_Prices = np.matmul(self.A_Materials, np.diag(get_prices([i for i in self.lookup], conn)))
        self.A_Products_Prices = np.matmul(self.A_Products, np.diag(get_prices([i for i in self.mat_dict], conn)))

        self.A_Mat_pInv = np.linalg.inv(self.A_Materials.T.dot(self.A_Materials))

        x = [sympy.Symbol(f"x{i}") for i in range(17)]  # x symbolic vector
        sym_value =  1 / (np.sum(self.A_Products_Prices.T.dot(x)))
        grad_sym_value = [sym_value.diff(xi) for xi in x]
        self.obj_fnc = sympy.lambdify([x], sym_value, 'numpy')
        self.grad_fnc = sympy.lambdify([x], grad_sym_value, 'numpy')

        # sym_profit = 1 / (np.sum(self.A_Products_Prices.T.dot(x)) - np.sum(self.A_Materials_Prices.T.dot(x)))
        # grad_sym_profit = [sym_profit.diff(xi) for xi in x]

        #

        #grad_sym_total = [sym_total.diff(xi) for xi in x]
        #sym_usage = np.sum((stock-self.A_Materials_mask_blocks.dot(x)).T.dot(stock - self.A_Materials_mask_blocks.dot(x)))
        #grad_sym_usage = [sym_usage.diff(xi) for xi in x]


        #self.obj_profit = sympy.lambdify([x], sym_profit, 'numpy')
        #self.grad_profit = sympy.lambdify([x], grad_sym_profit, 'numpy')

        #self.obj_total = sympy.lambdify([x,stock], sym_total, 'numpy')
        #self.grad_total = sympy.lambdify([x,stock], grad_sym_total, 'numpy')
        #self.obj_usage = sympy.lambdify([x,stock], sym_usage, 'numpy')
        #self.grad_usage = sympy.lambdify([x,stock], grad_sym_usage, 'numpy')


    def objective_value(self):
        x = [sympy.Symbol(f"x{i}") for i in range(17)]  # x symbolic vector
        sym_value =  1 / (np.sum(self.A_Products_Prices.T.dot(x)))
        grad_sym_value = [sym_value.diff(xi) for xi in x]
        self.obj_fnc = sympy.lambdify([x], sym_value, 'numpy')
        self.grad_fnc = sympy.lambdify([x], grad_sym_value, 'numpy')

    def objective_profit(self):
        x = [sympy.Symbol(f"x{i}") for i in range(17)]  # x symbolic vector
        sym_profit = 1 / (np.sum(self.A_Products_Prices.T.dot(x)) - np.sum(self.A_Materials_Prices.T.dot(x)))
        grad = [sym_profit.diff(xi) for xi in x]
        self.obj_fnc = sympy.lambdify([x], sym_profit, 'numpy')
        self.grad_fnc = sympy.lambdify([x], grad, 'numpy')

    def objective_total(self, stock):
        x = [sympy.Symbol(f"x{i}") for i in range(17)]  # x symbolic vector
        sym_total = 1 / (np.sum(self.A_Products_Prices.T.dot(x)) + np.sum(self.A_Input_Prices.T.dot((stock - self.A_Materials.T.dot(x)).T)))
        grad = [sym_total.diff(xi) for xi in x]
        self.obj_fnc = sympy.lambdify([x], sym_total, 'numpy')
        self.grad_fnc = sympy.lambdify([x], grad, 'numpy')

    def objective_usage(self, stock):
        x = [sympy.Symbol(f"x{i}") for i in range(17)]  # x symbolic vector
        sym_total = np.sum((stock-self.A_Materials_mask_blocks.dot(x)).T.dot(stock - self.A_Materials_mask_blocks.dot(x)))
        grad = [sym_total.diff(xi) for xi in x]
        self.obj_fnc = sympy.lambdify([x], sym_total, 'numpy')
        self.grad_fnc = sympy.lambdify([x], grad, 'numpy')

    def runs_to_materials(self, x):
        return self.A_Materials.T.dot(x)

    def runs_to_materials_prices(self, x):
        return self.A_Materials_Prices.T.dot(x)

    def runs_to_products(self, x):
        return self.A_Products.T.dot(x)

    def runs_to_products_prices(self, x):
        return self.A_Products_Prices.T.dot(x)

    def materials_prices(self, x):
        return self.A_Input_Prices.T.dot(x)

    def optimize(self, stock, profit=False):
        zeros = np.zeros((len(self.lookup),))
        x0 = np.ones((len(self.mat_dict),))

        # first simpler guess, optimize to use maximal resources
        bounds = scipy.optimize.Bounds(np.zeros((len(self.mat_dict),)), np.ones((len(self.mat_dict),)) * np.inf,
                                       keep_feasible=True)
        constraint = scipy.optimize.LinearConstraint(self.A_Materials_mask_blocks, zeros, stock,
                                                     keep_feasible=True)

        f = lambda xv: np.linalg.norm(self.A_Materials_mask_blocks.dot(xv) - stock)
        o_x00 = scipy.optimize.minimize(f, x0, bounds=bounds)
        o_mats = self.A_Materials.T.dot(o_x00['x'])

        # scale overshoot to be within constraints
        scale = 1.0
        for i in range(len(stock)):

            s = stock[i]
            m = np.array(o_mats)[0][i]
            if m > s > 0 and scale > s / m:
                scale = s / m
        # use this solution as good inital guess for more complex optimize
        x00 = o_x00['x'] * scale * 0.01

        output = scipy.optimize.minimize(self.obj_fnc, x00, method='SLSQP', jac=self.grad_fnc, bounds=bounds,
                                         constraints=constraint,
                                         options={'disp': True})
        print(output)

        return output['x']

    def optimize_residual(self, stock):
        zeros = np.zeros((len(self.lookup),))
        mask = np.ones((len(stock),))
        mask[0] = 0
        mask[1] = 0
        mask[2] = 0
        mask[3] = 0

        x0 = np.ones((len(self.mat_dict),))
        # first simpler guess, optimize to use maximal resources

        constait = {'type': 'ineq', 'fun': lambda x: np.min(-np.diag(mask).dot(self.A_Materials.T).dot(x) + np.diag(mask).dot(stock))}

        bounds = scipy.optimize.Bounds(np.zeros((len(self.mat_dict),)), np.ones((len(self.mat_dict),)) * np.inf,
                                       keep_feasible=True)

        f = lambda xv: np.linalg.norm(np.multiply(self.A_Materials.T.dot(xv) - stock, mask))
        output = scipy.optimize.minimize(f, x0, method='SLSQP', bounds=bounds, constraints=constait)
        o_mats = self.A_Materials.T.dot(output['x'])

        scale = 1.0
        for i in range(len(stock)):

            if i in [0,1,2,3]:
                continue

            s = stock[i]
            m = np.array(o_mats)[0][i]
            if m > s > 0 and scale > s / m:
                scale = s / m
        # use this solution as good inital guess for more complex optimize
        x00 = output['x'] * scale

        return x00

    def optimize_multipass(self, stock):
        zeros = np.zeros((len(self.lookup),))

        # first simpler guess, optimize to use maximal resources
        bounds = scipy.optimize.Bounds(np.zeros((len(self.mat_dict),)), np.ones((len(self.mat_dict),)) * np.inf,
                                       )
        constraint = scipy.optimize.LinearConstraint(self.A_Materials_mask_blocks, zeros, stock,
                                                     )
        result = self.optimize(stock)
        best = self.obj_fnc(result)

        for i in range(100):
            x0 = np.random.rand(17) * np.linalg.norm(stock)
            output = scipy.optimize.minimize(self.obj_fnc, x0, method='SLSQP', jac=self.grad_fnc, bounds=bounds,
                                             constraints=constraint)
            print(self.obj_fnc(output['x']))
            if self.obj_fnc(output['x']) < best:
                best = self.obj_fnc(output['x'])
                result = output['x']

        return result
