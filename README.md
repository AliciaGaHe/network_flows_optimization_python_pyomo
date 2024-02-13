Here we solve the network flows optimization problem propused by AIMMS in https://download.aimms.com/aimms/download/manuals/AIMMS3_OM.pdf using pyomo library of Python.

In this problem, we have two sources, located in Arnhem and Gouda, and six customers, located in London, Berlin, Maastricht, Amsterdam, Utrecht and The Hague. For reasons of efficiency, deliveries abroad are only made by one source. So that, Arnhem delivers to Berlin and Gouda to London.

We can find the original limits of production/supply for each source, the demand for each customer and transportation costs between each source and customer in data_0.json. In this problem, the goal is to satisfy the customers’ demand while minimizing transportation costs.

In main.py, we can find the problem formulation, the way to solve it using ‘cbc’ solver and a way to print the solution and the sensibility analysis for this solution (reduced costs for the production constraints and the shadow prices for the demand constraints).

We have four data file that we can use to try the code:
* data_0.json. This is the base case.
* data_1.json. We make a change in the input data to demostrate the reduced costs interpretation. Using base case, we move one ton of supply capacity from Gouda to Arnhem and the objetive function improves in 0.2 euros (reduced cost for Arnhem).
* data_2.json. We make a change in the input data to demostrate the shadow prices interpretation. Using base case, we increase the demand in London in one ton and we increase one ton of supply capacity in Gouda (Gouda is the only source for London). Then the objetive function gets worse in 2.5 euros (shadow Price for London).
* data_3.json. We make another change in the input data to demostrate the shadow prices interpretation. Using base case, we increase the demand in Berlin in one ton and we increase one ton of supply capacity in Gouda (Arnhem is the only source for Berlin). Then the objetive function gets worse in 2.7 euros (shadow price for Berlin).
* data_4.json. We make another change in the input data that activates ‘c03_fixed_transportations’ constraint. Using base case, we fixed a transportation between Arnhem and Utrecht equal to 149 tons. The flows between Arnhem and Amsterdam/Utrecht and Gouda and Amsterdam/Utrecht change, as well as the objective function. As we are doing something different of the base case (where all the flows are free), the solution is worse.