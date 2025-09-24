# 6 Hazard analysis and risk assessment

## 6.1 Objectives

The objectives of this clause are:

- a) to identify and to classify the hazardous events caused by malfunctioning behaviour of the item; and
- b) to formulate the safety goals with their corresponding ASILs related to the prevention or mitigation of the hazardous events, in order to avoid unreasonable risk.

## 6.2 General

Hazard analysis, risk assessment and ASIL determination are used to determine the safety goals for the item. For this, the item is evaluated with regard to its potential hazardous events. Safety goals and their assigned ASIL are determined by a systematic evaluation of hazardous events. The ASIL is determined by considering severity, probability of exposure and controllability. It is based on the item's functional behaviour; therefore, the detailed design of the item does not need to be known.

## 6.3 Inputs to this clause

### 6.3.1 Prerequisites

The following information shall be available:

- -  item definition in accordance with 5.5.1.

### 6.3.2 Further supporting information

The following information can be considered:

- -  relevant information on other items (from an external source).

## 6.4 Requirements and recommendations

### 6.4.1 Initiation of the hazard analysis and risk assessment

- 6.4.1.1 The hazard analysis and risk assessment shall be based on the item definition.
- 6.4.1.2 The item without internal safety mechanisms shall be evaluated during the hazard analysis and  risk  assessment,  i.e.  safety  mechanisms  intended  to  be  implemented  or  that  have  already  been implemented in predecessor items shall not be considered in the hazard analysis and risk assessment.
- NOTE 1 In  the  evaluation  of  an  item,  available  and  sufficiently  independent  external  measures  can  be beneficial.

EXAMPLE Electronic stability control can mitigate the effect of failures in chassis systems by increasing the controllability for the driver if it is shown to be available and independent from the item under evaluation.

NOTE 2 Safety  mechanisms  of  the  item  that  are  intended  to  be  implemented  or  that  have  already  been implemented are incorporated as part of the functional safety concept.

### 6.4.2 Situation	analysis and hazard	identification

- 6.4.2.1 The operational situations and operating modes in which an item's malfunctioning behaviour will result in a hazardous event shall be described; both when the vehicle is correctly used and when it is incorrectly used in a reasonably foreseeable way.
- NOTE 1 Operational situations describe conditions within which the item is assumed to behave in a safe manner.
- NOTE 2 Hazards resulting only from the item behaviour, in the absence of any item failure, are outside the scope of this document.
- 6.4.2.2 The hazards shall be determined systematically based on possible malfunctioning behaviour of the item.
- NOTE 1 FMEA approaches and HAZOP are suitable to support hazard identification at the item level. These can be supported by brainstorming, checklists, quality history, and field studies.
- NOTE 2 The responsibility to establish external measures to mitigate the additional risks from transporting goods is outside of the scope of ISO 26262. Therefore, the additional risks related to the transport of goods are not part of the hazard analysis and risk assessment.

- 6.4.2.3 Hazards caused by malfunctioning behaviour of the item shall be defined at the vehicle level.

- NOTE 1 In general, each hazard will have a variety of potential causes related to the item's implementation, but these causes do not need to be considered in the hazard analysis and risk assessment for the analysis of the malfunctioning behaviour.

NOTE 2 Only  hazards  associated  with  malfunctioning  behaviour  of  the  item  are  considered;  every  other system (external measure) is presumed to be functioning correctly provided it is sufficiently independent.

- 6.4.2.4 If  there are hazards identified in this clause that are outside of the scope of ISO 26262 (see Clause 1 ), then these hazards shall be addressed according to organization specific procedures.
- NOTE As these hazards are outside the scope of ISO 26262, this document does not provide guidance for ASIL  compliance  of  these  hazards.  Such  hazards  are  classified  according  to  the  procedures  of  the  applicable safety discipline.

- 6.4.2.5 Relevant hazardous events shall be determined.

- 6.4.2.6 The consequences of hazardous events shall be identified.

NOTE If  malfunctioning  behaviour  induces  the  loss  of  several  functions  of  the  item,  then  the  situation analysis and hazard identification consider the combined effects.

EXAMPLE 1 Loss of the functionality of a braking system (ESC) can lead to the simultaneous unavailability of driver assistance functions.

EXAMPLE 2 Failure of the vehicle's electrical power supply system can lead to a simultaneous loss of a number of functions including "engine torque", "power assisted steering" and "forward illumination".

- 6.4.2.7 It shall be ensured that the chosen level of detail of the list of operational situations does not lead to an inappropriate lowering of the ASIL.
- NOTE A  very  detailed  list  of  operational  situations  (see 6.4.2.1 ) for  one  hazard,  with  regard  to  the vehicle  state,  road  conditions  and  environmental  conditions,  can  lead  to  a  fine  granularity  of  situations  for the classification of hazardous events. This can make it easier to rate controllability and severity. However, a larger number of different operational situations can lead to a consequential reduction of the respective classes of  exposure,  and  thus  to  an  inappropriate  lowering  of  the  ASIL.  This  can  be  avoided  by  aggregating  similar situations.

### 6.4.3 Classification	of	hazardous	events

- 6.4.3.1 All  hazardous events identified in 6.4.2 shall  be  classified,  except  those  that  are  outside  the scope of ISO 26262.
- NOTE If  classification  of  a  given  hazard  with  respect  to  severity  (S),  probability  of  exposure  (E)  or controllability (C) is difficult to make, it is classified conservatively, i.e. whenever there is a reasonable doubt, a higher S, E or C classification is chosen.
- 6.4.3.2 The  severity  of  potential  harm  shall  be  estimated  based  on  a  defined  rationale  for  each hazardous event. The severity shall be assigned to one of the severity classes S0, S1, S2 or S3 in accordance with Table 1.
- NOTE 1 The risk assessment of hazardous events focuses on the harm to each person potentially at risk including the driver or the passengers of the vehicle causing the hazardous event, and other persons potentially at risk such as cyclists, pedestrians or occupants of other vehicles. The description of the Abbreviated Injury Scale (AIS) can be used for characterising the severity and can be found in Annex B, along with informative examples of different types of severity and accidents.
- NOTE 2 The severity class can be based on a combination of injuries, and this can lead to a higher classification of the severity than would result from just looking at a single injury.
- NOTE 3 The estimate considers reasonable sequences of events for the operational situation being evaluated.
- NOTE 4 The severity classification is based on a representative sample of persons at risk.

Table 1 - Classes of severity

|             | Class       | Class                       | Class                                                    | Class                                                          |
|-------------|-------------|-----------------------------|----------------------------------------------------------|----------------------------------------------------------------|
|             | S0          | S1                          | S2                                                       | S3                                                             |
| Description | No injuries | Light and moderate injuries | Severe and life-threatening injuries (survival probable) | Life-threatening injuries (survival uncertain), fatal injuries |

- 6.4.3.3 There  are  operational  situations  that  result  in  harm  (e.g.  an  accident).  A  subsequent malfunctioning behaviour of the item in such an operational situation can increase, or fail to decrease, the resulting harm. In this case the classification of the severity may be limited to the difference between the severity caused by the initial operational situation (e.g. the accident) and the malfunctioning behaviour of the item.
- EXAMPLE 1 If an accident occurs which is not caused by the malfunctioning behaviour of an item, the resulting harm from the accident is not considered for the classification of the severity.
- EXAMPLE 2 The  item  under  consideration  includes  an  airbag  functionality  to  reduce  harm  caused  by  the crash. For an accident in which the airbag fails to deploy, the harm caused by the crash can be determined. If a correctly operating airbag would have reduced the harm of the same accident to a lower severity class, then only the difference is considered for the severity classification.
- 6.4.3.4 The severity class S0 may be assigned if the hazard analysis and risk assessment determines that the consequences of a malfunctioning behaviour of the item are clearly limited to material damage. If a hazardous event is assigned severity class S0, no ASIL assignment is required.
- 6.4.3.5 The probability of exposure of each operational situation shall be estimated based on a defined rationale for each hazardous event. The probability of exposure shall be assigned to one of the probability classes, E0, E1, E2, E3 or E4 in accordance with Table 2.
- NOTE 1 For classes E1 to E4, the difference in probability from one E class to the next is an order of magnitude.
- NOTE 2 The exposure determination is based on a representative sample of operational situations for the target markets.
- NOTE 3 For further information and examples related to the probability of exposure see Annex B .
- 6.4.3.6 The number of vehicles equipped with the item shall not be considered when estimating the probability of exposure.
- NOTE The evaluation of the probability of exposure is performed assuming each vehicle is equipped with the item. This means that the argument 'the probability of exposure can be reduced, because the item is not present in every vehicle (as only some vehicles are equipped with the item)' is not valid.
- 6.4.3.7 Class E0 may be used for those operational situations that are suggested during hazard analysis and risk assessment, but that are considered incredible, and therefore not explored further. A rationale shall be recorded for the exclusion of these situations. If a hazardous event is assigned exposure class E0, no ASIL assignment is required.

Table 2 - Classes of probability of exposure regarding operational situations

|             | Class      | Class                | Class           | Class              | Class            |
|-------------|------------|----------------------|-----------------|--------------------|------------------|
|             | E0         | E1                   | E2              | E3                 | E4               |
| Description | Incredible | Very low probability | Low probability | Medium probability | High probability |

EXAMPLE E0 can be used in the case of 'force majeure' risk (see B.3).

- 6.4.3.8 The controllability  of  each  hazardous  event,  by  the  driver  or  other  persons  involved  in  the operational  situation  shall  be  estimated  based  on  a  defined  rationale  for  each  hazardous  event.  The controllability shall be assigned to one of the controllability classes C0, C1, C2 or C3 in accordance with Table 3.
- NOTE 1 For classes C1 to C3, the difference in probability from one C class to the next is an order of magnitude.
- NOTE 2 The evaluation of the controllability is an estimate of the probability that someone is able to gain sufficient control of the hazardous event, such that they are able to avoid the specific harm. For this purpose, the  parameter  C  is  used,  with  the  classes  C0,  C1,  C2  and  C3,  to  classify  the  potential  of  avoiding  harm.  It  is assumed that the driver is in an appropriate condition to drive (e.g. they are not tired), has the appropriate driver training (they have a driver's licence) and is complying with the applicable legal regulations, including due care requirements to avoid risks to other traffic participants. Some examples, which serve as an interpretation of these classes, are listed in Table B.6.
- NOTE 3 Reasonably foreseeable misuse is considered, e.g. 'not keeping the required distance to the vehicle in front as a common behaviour'.
- NOTE 4 Where  the  hazardous  event  is  not  related  to  the  control  of  the  vehicle  direction  and  speed,  e.g. potential limb entrapment in moving parts, the controllability can be an estimate of the probability that the person at risk is able to remove themselves, or to be removed by others from the hazardous situation. When considering controllability, note that the person at risk might not be familiar with the operation of the item or may not be aware that a potentially hazardous situation evolves.
- NOTE 5 When  controllability  involves the actions of multiple traffic participants, the controllability assessment can be based on the controllability of the vehicle with the malfunctioning item and the assumed action of other participants.

## Table 3 - Classes of controllability

|             | Class                   | Class               | Class                 | Class                                  |
|-------------|-------------------------|---------------------|-----------------------|----------------------------------------|
|             | C0                      | C1                  | C2                    | C3                                     |
| Description | Controllable in general | Simply controllable | Normally controllable | Difficult to control or uncontrollable |

- 6.4.3.9 Class C0 may be used for hazards addressing the unavailability of the item if they do not affect the safe operation of the vehicle (e.g. some driver assistance systems) or if an accident can be avoided by routine driver actions. If a hazardous event is assigned controllability class C0, no ASIL assignment is required.
- EXAMPLE 1 If loss of propulsion occurs in the garage when attempting to drive away from the house, C0 can be chosen as any driver can put the car back in park.
- NOTE Dedicated regulations that specify a functional performance with regard to the applicable hazardous event can be used as part of a rationale when selecting a suitable controllability class, if applicable, and supported by evidence, e.g. real usage experience.
- EXAMPLE 2 A dedicated regulation that covers the requirements for the certification of a vehicle system with a precise definition of forces or acceleration values in the case of a failure.
- 6.4.3.10 An ASIL shall be determined for each hazardous event based on the classification of severity, probability of exposure and controllability, in accordance with Table 4.
- NOTE 1 Four ASILs are defined: ASIL A, ASIL B, ASIL C and ASIL D, where ASIL A is the lowest safety integrity level and ASIL D the highest one.
- NOTE 2 In addition to these four ASILs, the class QM (quality management) denotes no requirement to comply with ISO 26262. Nevertheless, the corresponding hazardous event can have consequences with regards to safety and safety requirements can be formulated in this case. The classification QM indicates that quality processes are sufficient to manage the identified risk.

Table 4 - ASIL determination

| Severity class   | Exposure class   | Controllability class   | Controllability class   | Controllability class   |
|------------------|------------------|-------------------------|-------------------------|-------------------------|
| Severity class   | Exposure class   | C1                      | C2                      | C3                      |
|                  | E1               | QM                      | QM                      | QM                      |
|                  | E2               | QM                      | QM                      | QM                      |
|                  | E3               | QM                      | QM                      | A                       |
|                  | E4               | QM                      | A                       | B                       |
|                  | E1               | QM                      | QM                      | QM                      |
|                  | E2               | QM                      | QM                      | A                       |
|                  | E3               | QM                      | A                       | B                       |
|                  | E4               | A                       | B                       | C                       |
|                  | E1               | QM                      | QM                      | A a                     |
|                  | E2               | QM                      | A                       | B                       |
|                  | E3               | A                       | B                       | C                       |
|                  | E4               | B                       | C                       | D                       |

6.4.3.11 If several unlikely situations are combined that result in a lower probability of exposure than E1, QM may be argued for S3, C3 based on this combination.

EXAMPLE 1 For  the  malfunction  of  a  high  voltage  system  erroneously  supplying  power.  The  combined operational situations are:

- -a crash which deploys the airbag;
- -with the vehicle lying partly in the water; and
- -the high voltage system partially exposed without causing an internal short circuit.

EXAMPLE 2 For  the  malfunction  of  a  fuel  pump  supplying  petrol  erroneously.  The  combined  operational situations are:

- -a crash which deploys the airbag;
- -the tank system behind the pump remains fully functional;
- -the fuel line from the pump is broken, such that petrol can drip on hot parts; and
- -the energy supply of the pump is fully functional.

### 6.4.4 Determination of safety goals

6.4.4.1 A  safety  goal  shall  be  determined  for  each  hazardous  event  with  an  ASIL  evaluated  in  the hazard analysis and risk assessment. If similar safety goals are determined, these may be combined into one safety goal.

NOTE Safety  goals  are  top-level  safety  requirements  for  the  item.  They  lead  to  the  functional  safety requirements needed to avoid an unreasonable risk for each hazardous event. Safety goals are not expressed in terms of technological solutions, but in terms of functional objectives.

- 6.4.4.2 The ASIL determined for the hazardous event shall be assigned to the corresponding safety goal. If similar safety goals are combined into a single one, in accordance with 6.4.4.1 , the highest ASIL shall be assigned to the combined safety goal.

6.4.4.3 The safety goals together with their ASIL shall be specified in accordance with ISO 26262-8:2018, Clause 6.

NOTE The safety goal can specify the fault tolerant time interval, or physical characteristics (e.g. a maximum level of unwanted steering-wheel torque, maximum level of unwanted acceleration) if they were relevant to the ASIL determination.

- 6.4.4.4 Assumptions used for, or resulting from the hazard analysis and risk assessment which are relevant for ASIL determination (if applicable, including hazardous events classified QM or with no ASIL assigned) shall be identified. These assumptions shall be validated in accordance with ISO 26262-4:2018, Clause 8 for the integrated item.

NOTE Assumptions, if any, that are considered during the HARA include assumed actions of the driver or persons at risk and assumptions regarding external measures.

### 6.4.5 Management of variances of T&amp;B in hazard analysis and risk assessment

- 6.4.5.1 The requirements in 6.4.5 shall only be applied to T&amp;B.
- 6.4.5.2 The  following  variances  shall  be  considered  when  conducting  a  hazard  analysis  and  risk assessment for a T&amp;B vehicle:
- a) type of base vehicle;
- b) the T&amp;B vehicle configuration; and
- c) the T&amp;B vehicle operation.

NOTE Engineering judgement is appropriate when selecting variance types for the analysis.

EXAMPLE 1 Wheel spin may only be relevant for unloaded trucks which is not as common as loaded trucks, thereby affecting probability of exposure.

- EXAMPLE 2 An attached trailer may reduce driver's controllability of the vehicle when compared to no trailer attached for certain hazards, thereby affecting controllability.
- EXAMPLE 3 Different T&amp;B bodies may have different safety properties, thereby affecting severity.
- 6.4.5.3 When conducting a hazard analysis and risk assessment each relevant type of base vehicle shall be considered.
- 6.4.5.4 The number of vehicles of a given type of base vehicle shall not be considered when estimating the probability of exposure.
- 6.4.5.5 The number of vehicles equipped with a specific configuration shall not be considered when estimating the probability of exposure.
- 6.4.5.6 When conducting a hazard analysis and risk assessment the variances in operational situations that have impact on technical parameters shall be considered.
- NOTE 1 The use of the vehicle is part of the considered operational situation and is considered when estimating the probability of exposure.
- EXAMPLE 1 Driving a tractor without a semi-trailer attached results in a low load on the drive axle (technical parameter) which leads to a reduction of vehicle dynamics stability. When estimating the probability of exposure, the operational situation would be for example: "Driving a tractor on public roads without a semi-trailer". With reference to Table B.4 , this scenario could be classified as E2.
- NOTE 2 When conducting a hazard analysis and risk assessment, the body application can be considered as cargo. Variations in the cargo can be considered.
- EXAMPLE 2 Variations in loading condition (full, partial, empty) and position of centre of gravity.

- NOTE 3 Functions of body builder equipment, especially machinery functions, can be in scope of other safety standards.  Hazard  analysis  and  risk  assessment  for  these  functions  is  done  following  the  specific  applicable safety standards.
- NOTE 4 For functions of the vehicle that are designed to support dedicated body applications the operational situations of the body can be considered during the hazard analysis and risk assessment.
- 6.4.5.7 When  classifying  the  parameters  Severity,  Exposure  and  Controllability,  an  appropriate combination of the variance types for an item shall be considered.

NOTE The appropriate combination can be determined based on engineering judgement.

### 6.4.6 Verification

- 6.4.6.1 The  hazard  analysis  and  risk  assessment  including  the  safety  goals  shall  be  verified  in accordance with ISO 26262-8:2018, Clause 9, to provide evidence for the:
- a) appropriate  selection  with  regard  to  operational  situations  and  hazard  identification  (and  T&amp;B vehicle configuration);
- b) compliance with the item definition;
- c) consistency with related hazard analyses and risk assessments of other items;
- d) completeness of the coverage of the hazardous events; and
- e) consistency of the safety goals with the assigned ASILs and the corresponding hazardous events.

## 6.5 Work products

- 6.5.1 Hazard analysis and risk assessment report resulting from requirements in 6.4.1 to 6.4.5.
- 6.5.2 Verification	report	of	the	hazard	analysis	and	risk	assessment resulting from requirement 6.4.6.