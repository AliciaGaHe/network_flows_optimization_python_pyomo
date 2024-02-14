# Import from libraries
import pandas as pd

from pyomo.environ import (
    AbstractModel,
    Suffix,
    Set,
    Param,
    Var,
    Constraint,
    Objective,
    NonNegativeReals,
    minimize,
    DataPortal,
    SolverFactory,
    value
)

from pyomo.opt import (
    SolverStatus,
    TerminationCondition
)


def create_model():
    """create linear programming model for network flows optimization problem"""
    # Create an abstract model
    model = AbstractModel()

    # Import constraint dual information for sensibility analysis
    model.dual = Suffix(direction=Suffix.IMPORT)

    # Import variable reduced cost information for sensibility analysis
    model.rc = Suffix(direction=Suffix.IMPORT)

    # Create sets
    # Sources
    model.sSources = Set()
    # Customers
    model.sCustomers = Set()
    # Arcs between sources and customers
    model.sSources_sCustomers = Set(dimen=2)

    # Create parameters
    # Production of each source
    model.pSourceProduction = Param(model.sSources, mutable=True)
    # Demand of each customer
    model.pCustomerDemand = Param(model.sCustomers, mutable=True)
    # Transportation cost between each source and customer
    model.pTransportationCosts = Param(model.sSources_sCustomers, mutable=True)
    # Quantity that is mandatory to move between each source and customer
    model.pFixedTransportation = Param(model.sSources_sCustomers, mutable=True)

    # Create variables
    # Quantity of products transported between each source and customer
    model.vQuantityExchangedSourceCustomer = Var(model.sSources_sCustomers, domain=NonNegativeReals, initialize=0)

    # Create constraints
    def c01_production_limit_satisfaction(model, iSource):
        """production limit for each source"""
        return (
                sum(
                    model.vQuantityExchangedSourceCustomer[iSource, iCustomer]
                    for iCustomer in model.sCustomers
                    if (iSource, iCustomer) in model.sSources_sCustomers
                )
                <= model.pSourceProduction[iSource]
        )

    def c02_demand_limit_satisfaction(model, iCustomer):
        """demand limit for each customer"""
        return (
                sum(
                    model.vQuantityExchangedSourceCustomer[iSource, iCustomer]
                    for iSource in model.sSources
                    if (iSource, iCustomer) in model.sSources_sCustomers
                )
                >= model.pCustomerDemand[iCustomer]
        )

    def c03_fixed_transportations(model, iSource, iCustomer):
        """quantity that is mandatory to move between each source and each customer"""
        if (iSource, iCustomer) in model.sSources_sCustomers and value(model.pFixedTransportation[iSource, iCustomer]):
            return (
                    model.vQuantityExchangedSourceCustomer[iSource, iCustomer]
                    == model.pFixedTransportation[iSource, iCustomer]
            )
        else:
            return Constraint.Skip

    # Create the objective function
    def obj_expression(model):
        """minimum total transportation cost"""
        return (
                sum(
                    model.pTransportationCosts[iSource, iCustomer] *
                    model.vQuantityExchangedSourceCustomer[iSource, iCustomer]
                    for iSource in model.sSources
                    for iCustomer in model.sCustomers
                    if (iSource, iCustomer) in model.sSources_sCustomers
                )
        )

    # Active constraints
    model.c01_production_limit_satisfaction = Constraint(
        model.sSources, rule=c01_production_limit_satisfaction
    )

    model.c02_demand_limit_satisfaction = Constraint(
        model.sCustomers, rule=c02_demand_limit_satisfaction
    )

    model.c03_fixed_transportations = Constraint(
        model.sSources, model.sCustomers, rule=c03_fixed_transportations
    )

    # Add objective function
    model.f_obj = Objective(rule=obj_expression, sense=minimize)

    # Return the model
    return model


def load_data_json_format(data_file):
    """load data for the problem to solve in json format"""
    # Create a DataPortal object
    data = DataPortal()

    # Load a file with data in json format
    data.load(filename=data_file)

    # Return the data
    return data


def print_conclusions_sources_sensibility_analysis(shadow_price, source):
    """print conclusions of the source sensibility analysis"""
    if shadow_price < 0:
        print("The total transportation cost would be reduced by",
              abs(shadow_price),
              "euros for each additional ton available in", source)
    elif shadow_price > 0:
        print("The total transportation cost would be increased in",
              shadow_price,
              "euros for each additional ton available in", source)
    else:
        print("The total transportation cost would remain equal for each additional ton available in", source)


def print_conclusions_customers_sensibility_analysis(shadow_price, customer):
    """print conclusions of the customer sensibility analysis"""
    if shadow_price < 0:
        print("The total transportation cost would be reduced by",
              abs(shadow_price),
              "euros for each additional ton supply at", customer)
    elif shadow_price > 0:
        print("The total transportation cost would be increased in",
              shadow_price,
              "euros for each additional ton supply at", customer)
    else:
        print("The total transportation cost would remain equal for each additional ton supply at", customer)


def print_conclusions_routes_sensibility_analysis(reduced_cost, source, customer):
    """print conclusions of the routes sensibility analysis"""
    if reduced_cost < 0:
        print("The total transportation cost would be reduced by",
              abs(reduced_cost),
              "euros for each ton supply from", source, "to", customer)
    elif reduced_cost > 0:
        print("The total cost would be increased in",
              reduced_cost,
              "euros for each ton supply from", source, "to", customer)
    else:
        print("The total transportation cost would remain equal for each ton supply from", source, "to", customer)


def solve_problem_and_print_results(data_file):
    """solve the problem and print results"""
    # Load data
    data = load_data_json_format(data_file)
    # Create the model
    model = create_model()
    # Create the instance to solve (a concrete model using the abstract model and data)
    instance = model.create_instance(data)

    # If we want to check the instance type ('pyomo.core.base.PyomoModel.ConcreteModel')
    # print(type(instance))
    # If we want to check if the instance is constructed
    # print(instance.is_constructed())
    # If we want to review the instance
    # instance.pprint()

    # Solve the instance using 'cbc' solver (we could use another one)
    # We can change some solver options before solving (such as the maximum time limit),
    # but it is not relevant in this problem because it is easy to solve
    opt = SolverFactory("cbc")
    # opt.options["seconds"] = 100
    results = opt.solve(instance)

    # Print results
    # If the solution is feasible and optimal...
    if ((results.solver.termination_condition == TerminationCondition.optimal) and
            (results.solver.status == SolverStatus.ok)):
        print("Solver status: ", results.solver.status)
        print("Termination condition: ", results.solver.termination_condition, "\n")

        print("Total transportation cost: ", instance.f_obj(), "\n")

        print("Quantity exchanged between sources and customers:")
        dict_quantity_sources_customers = {
            (iSource, iCustomer): value(instance.vQuantityExchangedSourceCustomer[iSource, iCustomer])
            for iSource in instance.sSources
            for iCustomer in instance.sCustomers
            if (iSource, iCustomer) in instance.sSources_sCustomers and
            value(instance.vQuantityExchangedSourceCustomer[iSource, iCustomer]) > 0
        }
        df_quantity_sources_customers = pd.DataFrame(
            dict_quantity_sources_customers.values(),
            index=pd.MultiIndex.from_tuples(dict_quantity_sources_customers.keys()),
            columns=['Quantity']
        ).reset_index(names=['Source', 'Customer'])
        print(df_quantity_sources_customers)
        print("\n")

        print("Sources sensibility analysis:")
        dict_source_sensibility_analysis = {
            iSource: [
                value(instance.pSourceProduction[iSource]),
                value(instance.c01_production_limit_satisfaction[iSource]),
                value(instance.dual[instance.c01_production_limit_satisfaction[iSource]])
            ]
            for iSource in instance.sSources
        }
        df_source_sensibility_analysis = pd.DataFrame(
            dict_source_sensibility_analysis.values(),
            index=pd.Index(dict_source_sensibility_analysis.keys()),
            columns=['Capacity', 'Shipped', 'Shadow price']
            ).reset_index(names=['Source'])
        print(df_source_sensibility_analysis)

        # Conclusions for resources without slack
        df_source_sensibility_analysis[
            df_source_sensibility_analysis['Capacity'] == df_source_sensibility_analysis['Shipped']
        ].apply(
            lambda row:
            print_conclusions_sources_sensibility_analysis(row['Shadow price'], row['Source']), axis=1)
        print("\n")

        print("Customers sensibility analysis:")
        dict_customers_sensibility_analysis = {
            iCustomer: [
                value(instance.pCustomerDemand[iCustomer]),
                value(instance.c02_demand_limit_satisfaction[iCustomer]),
                value(instance.dual[instance.c02_demand_limit_satisfaction[iCustomer]])
            ]
            for iCustomer in instance.sCustomers
        }
        df_customers_sensibility_analysis = pd.DataFrame(
            dict_customers_sensibility_analysis.values(),
            index=pd.Index(dict_customers_sensibility_analysis.keys()),
            columns=['Demand', 'Shipped', 'Shadow price']
            ).reset_index(names=['Customer'])
        print(df_customers_sensibility_analysis)

        # Conclusions for customer margin
        df_customers_sensibility_analysis[
            df_customers_sensibility_analysis['Demand'] == df_customers_sensibility_analysis['Shipped']
        ].apply(
            lambda row:
            print_conclusions_customers_sensibility_analysis(row['Shadow price'], row['Customer']), axis=1)
        print("\n")

        print("Routes sensibility analysis:")
        dict_routes_sensibility_analysis = {
            (iSource, iCustomer): [
                value(instance.vQuantityExchangedSourceCustomer[iSource, iCustomer]),
                value(instance.rc[instance.vQuantityExchangedSourceCustomer[iSource, iCustomer]])
            ]
            for iSource in instance.sSources
            for iCustomer in instance.sCustomers
            if (iSource, iCustomer) in instance.sSources_sCustomers
        }
        df_routes_sensibility_analysis = pd.DataFrame(
            dict_routes_sensibility_analysis.values(),
            index=pd.MultiIndex.from_tuples(dict_routes_sensibility_analysis.keys()),
            columns=['Quantity', 'Reduced cost']
        ).reset_index(names=['Source', 'Customer'])
        print(df_routes_sensibility_analysis)

        # Conclusions for routes without quantity
        df_routes_sensibility_analysis[
            df_routes_sensibility_analysis['Quantity'] == 0
        ].apply(
            lambda row:
            print_conclusions_routes_sensibility_analysis(row['Reduced cost'], row['Source'], row['Customer']), axis=1)
        print("\n")

    # If the solution in infeasible...
    elif results.solver.termination_condition == TerminationCondition.infeasible:
        print("\n")
        print("Solver status: ", results.solver.status)
        print("Termination condition: ", results.solver.termination_condition)
        print("\n")
        print(results.write())

    # If something else is wrong...
    else:
        print("\n")
        print("Solver status: ", results.solver.status)
        print("Termination condition: ", results.solver.termination_condition)


# Solve some transportation problems

# Base case
solve_problem_and_print_results("./data/data_0.json")

# Sensibility analysis - sources
# Using the base case, we move one ton of supply capacity from Gou to Arn and
# the objetive function improves in 0.2 euros (shadow price for Arn in the base case)
# solve_problem_and_print_results("./data/data_1.json")

# Sensibility analysis - customers - 1
# Using the base case, we increase the demand in Lon in one ton, and
# we increase one ton of supply capacity in Gou (Gou is the only source for Lon).
# Then the objetive function gets worse in 2.5 euros (shadow price for Lon in the base case)
# solve_problem_and_print_results("./data/data_2.json")

# Sensibility analysis - customers - 2
# Using the base case, we increase the demand in Ber in one ton, and
# we increase one ton of supply capacity in Gou (Arn is the only source for Ber).
# Then the objetive function gets worse in 2.7 euros (shadow price for Ber in the base case)
# solve_problem_and_print_results("./data/data_3.json")

# Sensibility analysis - routes
# Using the base case, we fixed a transportation between Arn and Ams equal to 1 ton,
# using pFixedTransportation and c03_fixed_transportations.
# The objetive function gets worse in 0.6 euros (reduced cost for the transportation between Arn and Ams)
# solve_problem_and_print_results("./data/data_4.json")
