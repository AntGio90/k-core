# 5 Item definition

## 5.1 Objectives

The objectives of this clause are:

- a) to define and describe the item, its functionality, dependencies on, and interaction with, the driver, the environment and other items at the vehicle level; and
- b) to support an adequate understanding of the item so that the activities in subsequent phases can be performed.

## 5.2 General

This clause lists  the  requirements  and  recommendations for establishing the definition of the item, including  its  functionality,  interfaces,  environmental  conditions,  legal  requirements  and  hazards. This definition serves to provide sufficient information about the item to the persons who conduct the subsequent sub-phases: 'Hazard analysis and risk assessment' (see Clause 6 ) and 'Functional safety concept' (see Clause 7).

NOTE Table A.1 provides an overview of objectives, prerequisites and work products of the concept phase.

## 5.3 Inputs to this clause

### 5.3.1 Prerequisites

None.

### 5.3.2 Further supporting information

The following information can be considered:

- -  any information that already exists concerning the item, e.g. a product idea, a project sketch, relevant patents, the results of pre-trials, the documentation from predecessor items, relevant information on other items.

## 5.4 Requirements and recommendations

### 5.4.1 The requirements of the item shall be made available, including:

NOTE 1 Requirements can be classified as safety-related after safety goals and their respective ASIL have been defined.

NOTE 2 If the functional and non-functional requirements are not already available, their generation can be triggered by the requirements of this clause.

- a) legal requirements, national and international standards;
- b) the functional behaviour at the vehicle level, including the operating modes or states;
- c) the required quality, performance and availability of the functionality, if applicable;
- d) constraints regarding the item such as functional dependencies, dependencies on other items, and the operating environment;
- e) potential consequences of behavioural shortfalls including known failure modes and hazards, if any; and

NOTE 3 This can include known safety-related incidents including similar items.

- f) the capabilities of the actuators, or their assumed capabilities.
- NOTE 4 These values (e.g. torque output, force exerted, speed of operation, brightness, loudness), or their estimates, are necessary to determine the magnitude of the effect when performing the hazard analysis and risk assessment. The magnitude of the effect is taken into account when deciding the values of severity and controllability.
- 5.4.2 The boundary of the item, its interfaces, and the assumptions concerning its interaction with other items and elements, shall be defined considering:
- a) the elements of the item;
- NOTE 1 The elements can also be based on other technology.
- b) the assumptions concerning the effects of the item's behaviour on the vehicle;
- c) the functionality of the item under consideration required by other items and elements;
- d) the functionality of other items and elements required by the item under consideration;
- e) the allocation and distribution of functions among the involved systems and elements; and
- f) the operational scenarios which impact the functionality of the item.

NOTE 2 With increasing complexity of vehicle functions, there are dependencies between items. One item can be realized by an array of systems that themselves implement other vehicle level functions, i.e. can be considered as items in their own right.

EXAMPLE A combined adaptive cruise control and lane keeping assist function is implemented in a braking system, a steering system and a propulsion system. In this example the braking system implements the service braking function, which can be considered an item in its own right.

NOTE 3 If the scope of the development is an element and not an item, then refer to ISO 26262-2:2018, 6.4.5.7.

## 5.5 Work products

- 5.5.1 Item definition resulting from requirements in 5.4.