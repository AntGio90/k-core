# 7 Functional safety concept

## 7.1 Objectives

The objectives of this clause are:

- a) to  specify  the  functional  or  degraded  functional  behaviour  of  the  item  in  accordance  with  its safety goals;
- b) to specify the constraints regarding suitable and timely detection and control of relevant faults in accordance with its safety goals;
- c) to specify the item level strategies or measures to achieve the required fault tolerance or adequately mitigate the effects of relevant faults by the item itself, by the driver or by external measures;
- d) to allocate the functional safety requirements to the system architectural design, or to external measures; and
- e) to verify the functional safety concept and specify the safety validation criteria.

## 7.2 General

To  comply  with  the  safety  goals,  the  functional  safety  concept  contains  safety  measures,  including the safety mechanisms, to be implemented in the item's architectural elements and specified in the functional safety requirements.

Figure 2 illustrates the hierarchical approach by which the safety goals are determined as a result of the hazard analysis and risk assessment. The functional safety requirements are then derived from the safety goals and are allocated to the system architectural design.

Using  preliminary  architectural  assumptions  provides  a  means  to  handle  immature  architectural information in early development phases.

For the structure and distribution of safety requirements within the corresponding Parts of ISO 26262, see ISO 26262-8:2018, Figure 2.

<!-- image -->

NOTE Within  the  figure,  the  specific  clauses  of  each  part  of  ISO  26262  are  indicated  in  the  following manner: 'm-n', where 'm' represents the number of the part and 'n' indicates the number of the clause, e.g. '3-6' represents ISO 26262-3:2018, Clause 6.

Figure 2 - Hierarchy of safety goals and functional safety requirements

## 7.3 Inputs to this clause

### 7.3.1 Prerequisites

The following information shall be available:

- -  item definition in accordance with 5.5.1 ;
- -  hazard analysis and risk assessment report in accordance with 6.5.1 ; and
- -  system architectural design (from an external source).

### 7.3.2 Further supporting information

The following information can be considered:

None.

## 7.4 Requirements and recommendations

### 7.4.1 General

The functional safety requirements shall be specified in accordance with ISO 26262-8:2018, Clause 6.

### 7.4.2 Derivation of functional safety requirements

- 7.4.2.1 The  functional  safety  requirements  shall  be  derived  from  the  safety  goals,  considering  the system architectural design.
- 7.4.2.2 At least one functional safety requirement shall be derived from each safety goal.

NOTE The same functional safety requirement can be derived from several safety goals (see Figure 2).

- 7.4.2.3 The functional safety requirements shall specify, if applicable, strategies for:
- a) fault avoidance;
- b) fault detection and control of faults or the resulting malfunctioning behaviour;
- c) transitioning to a safe state, and if applicable, from a safe state;
- d) fault tolerance;
- e) the degradation of the functionality in the presence of a fault and its interaction with f) or g);

EXAMPLE Maintaining the vehicle in a limp-home mode until the ignition has been switched from "on" to "off".

- f) driver warnings needed to reduce the risk exposure time to an acceptable duration;
- g) driver  warnings  needed  to  increase  the  controllability  by  the  driver  (e.g.  engine  malfunction indicator lamp, ABS fault warning lamp);
- h) how timing requirements at the vehicle level are met, i.e. how the fault tolerant time interval shall be met by defining a fault handling time interval; and
- i) avoidance  or  mitigation  of  a  hazardous  event  due  to  improper  arbitration  of  multiple  control requests generated simultaneously by different functions.

NOTE List items c), e), f) and g) can be part of the warning and degradation strategy.

- 7.4.2.4 Each  functional  safety  requirement  shall  be  specified  by  considering  the  following,  as applicable:
- a) operating modes;
- b) fault tolerant time interval;
- c) safe states;
- d) emergency operation time interval; and
- e) functional redundancies (e.g. fault tolerance).

NOTE This  activity  can  be  supported  by  safety  analyses  (e.g.  FMEA,  FTA,  HAZOP)  in  order  to  develop  a complete set of effective functional safety requirements.

- 7.4.2.5 If a safety goal violation can be prevented by transitioning to, or by maintaining, one or more safe states, then the corresponding safe state(s) shall be specified.

EXAMPLE A safe state could be "switched off", "locked", "vehicle stationary and maintained", or "reduced functionality" in the case of a failure over a defined time.

- 7.4.2.6 If a safe state cannot be reached by a transition within an acceptable time interval, an emergency operation shall be specified.
- 7.4.2.7 If assumptions are made about the necessary actions of the driver, or other persons, in order to prevent the violation of a safety goal, then the following shall apply:
- NOTE 1 The actions include those for which credit was taken during controllability estimation, and any further necessary actions taken to comply with the safety goals after the implementation of the safety requirements.
- EXAMPLE Adaptive cruise control: the ACC generated brake activation being overridden when the driver presses the accelerator pedal.
- a) these actions shall be specified in the functional safety concept; and
- b) the adequate means and controls available to the driver or other persons shall be specified in the functional safety concept.

NOTE 2 Driver task analysis can be helpful to consider prevention of driver overload, prevention of driver surprise or panic (loss of capability to control vehicle), and mode confusion (an incorrect assumption about the operating mode).

- NOTE 3 The specification of the warning and degradation strategy and the necessary actions of the driver and other persons potentially at risk are a potential input for the user's manual (see ISO 26262-7:2018, Clause 5).
- 7.4.2.8 The  functional  safety  requirements  shall  be  allocated  to  the  elements  of  the  system architectural design:
- a) During requirement allocation, the ASIL and information given in 7.4.2.4 shall be inherited from the associated safety goal. If ASIL decomposition is applied then the requirements of ISO 26262-9:2018, Clause 5 are also applicable.
- b) If  freedom  from  interference  in  accordance  with  ISO  26262-9:2018,  Clause  6  between  elements implementing safety requirements cannot be argued in the system architectural design, then the architectural  elements  shall  be  developed  in  accordance  with  the  highest  ASIL  for  those  safety requirements.
- c) If the item comprises more than one E/E system, then the functional safety requirements for the individual E/E systems and their interfaces shall be specified, considering the system architectural design. These functional safety requirements shall be allocated to the E/E systems.
- d) If the item comprises more than one E/E system then the corresponding target values for random hardware fault metrics (see ISO 26262-5:2018, Clauses 8 and 9) can be specified and allocated to each individual E/E system in accordance with ISO 26262-4:2018, 6.4.5.2.
- NOTE 1 The  specification  of  E/E  system  target  values  is  done  according  to  the  system  architectural design and further refined during the development phases.
- e) If ASIL decomposition is applied during the allocation of the functional safety requirements, then it shall be applied in accordance with ISO 26262-9:2018, Clause 5.
- NOTE 2 Independence can be verified by an analysis of dependent failures (see ISO 26262-9:2018, Clause 7).
- 7.4.2.9 If  the  functional  safety  concept  relies  on  elements  of  other  technologies,  then  the  following shall apply:
- a) the functional safety requirements implemented by elements of other technologies shall be derived and allocated to the corresponding elements of the architecture;

- b) the functional safety requirements relating to the interfaces with elements of other technologies shall be specified;
- c) the implementation of functional safety requirements by elements of other technologies shall be ensured through specific measures that are outside the scope of ISO 26262; and
- d) no ASIL should be assigned to safety requirements allocated to these elements.
- NOTE 1 A  proper  safety  attribute  can  be  assigned  to  safety  requirements  allocated  to  elements  of  other technologies;  and  the  concept  of  ASIL  decomposition,  described  in  ISO  26262-9:2018  Clause  5,  could  be extrapolated to the allocation of functional safety requirements to these elements. In this case, the appropriate implementation and verification rules are defined in addition to ISO 26262.
- NOTE 2 Evidence  for  the  adequacy  of  elements  of  other  technologies  is  provided  during  safety  validation activities (see ISO 26262-4:2018, Clause 8).
- 7.4.2.10 If the functional safety concept relies on external measures, then the following shall apply:
- a) the  functional  safety  requirements  implemented  by  external  measures  shall  be  derived  and communicated;
- b) the functional safety requirements of interfaces with external measures shall be specified; and
- c) if  the  external  measures  are  implemented  by  one  or  more  E/E  systems,  the  functional  safety requirements shall be addressed using ISO 26262.
- NOTE Evidence for the adequacy of external measures is provided during safety validation activities (see ISO 26262-4:2018, Clause 8).

### 7.4.3 Safety validation criteria

- 7.4.3.1 The  acceptance  criteria  for  safety  validation  of  the  item  shall  be  specified  based  on  the functional safety requirements and the safety goals.
- NOTE 1 For further requirements on detailing the criteria and a list of characteristics to be validated (see ISO 26262-4:2018, Clause 8).
- NOTE 2 Safety validation of the safety goals is addressed on the upper right of the V cycle but is included in the activities during development and not only performed at the end of development.

### 7.4.4 Verification	of	the	functional	safety	concept

- 7.4.4.1 The functional safety concept shall be verified in accordance with ISO 26262-8:2018, Clause 9, to provide evidence for:
- a) its consistency and compliance with the safety goals; and
- b) its ability to mitigate or avoid the hazards.
- NOTE 1 Verification of the ability to mitigate or avoid a hazard can be carried out during the concept phase to evaluate the safety concept and indicate where concept improvements are needed. This verification can be based on the same methods that are used for safety validation. However, the safety validation undertaken (to fulfil ISO 26262-4:2018, Clause 8) cannot be based on concept studies alone (e.g. prototypes).
- EXAMPLE The ability to mitigate or to avoid a hazard can be evaluated by tests, trials or expert judgement; with prototypes, studies, subject tests, or simulations.
- NOTE 2 The verification of the ability to mitigate or to avoid a hazard addresses the characteristics of the fault (e.g. being transient or permanent).
- NOTE 3 For verification, a traceability based argument can be used, i.e. the item complies with the safety goals if the item complies with the functional safety requirements.

## 7.5 Work products

- 7.5.1 Functional safety concept resulting from requirements in 7.4.1 to 7.4.3.
- 7.5.2 Verification	report	of	the	functional	safety	concept resulting from requirements in 7.4.4.