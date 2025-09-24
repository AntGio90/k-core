# Road vehicles - Functional safety -

# Part 3: Concept phase

## 1 Scope

This document is intended to be applied to safety-related systems that include one or more electrical and/or electronic (E/E) systems and that are installed in series production road vehicles, excluding mopeds. This document does not address unique E/E systems in special vehicles such as E/E systems designed for drivers with disabilities.

NOTE Other dedicated application-specific safety standards exist and can complement the ISO 26262 series of standards or vice versa.

Systems and their components released for production, or systems and their components already under development prior to the publication date of this document, are exempted from the scope of this edition. This document addresses alterations to existing systems and their components released for production prior to the publication of this document by tailoring the safety lifecycle depending on the alteration. This document addresses integration of existing systems not developed according to this document and systems developed according to this document by tailoring the safety lifecycle.

This document addresses possible hazards caused by malfunctioning behaviour of safety-related E/E systems, including interaction of these systems. It does not address hazards related to electric shock, fire, smoke, heat, radiation, toxicity, flammability, reactivity, corrosion, release of energy and similar hazards, unless directly caused by malfunctioning behaviour of safety-related E/E systems.

This  document  describes  a  framework  for  functional  safety  to  assist  the  development  of  safetyrelated E/E systems. This framework is intended to be used to integrate functional safety activities into a company-specific development framework. Some requirements have a clear technical focus to implement functional safety into a product; others address the development process and can therefore be seen as process requirements in order to demonstrate the capability of an organization with respect to functional safety.

This document does not address the nominal performance of E/E systems.

This document specifies the requirements for the concept phase for automotive applications, including the following:

- -  item definition;
- -  hazard analysis and risk assessment; and
- -  functional safety concept.

Annex A provides an overview on objectives, prerequisites and work products of this document.

## 2 Normative references

The following documents are referred to in the text in such a way that some or all of their content constitutes  requirements of this document. For dated references, only the edition cited applies. For undated references, the latest edition of the referenced document (including any amendments) applies.

ISO 26262-1, Road Vehicles - Functional Safety - Part 1: Vocabulary

ISO 26262-2:2018, Road Vehicles - Functional Safety - Part 2: Management of functional safety

ISO 26262-4:2018, Road vehicles - Functional safety - Part 4: Product development at the system level

ISO 26262-8:2018, Road vehicles - Functional safety - Part 8: Supporting processes

ISO 26262-9:2018, Road vehicles - Functional safety - Part 9: Automotive Safety Integrity Level (ASIL)- oriented and safety-oriented analyses

## 3 Terms	and	definitions

For  the  purposes  of  this  document,  the  terms,  definitions  and  abbreviated  terms  given  in ISO 26262-1 apply.

ISO and IEC maintain terminological databases for use in standardization at the following addresses:

- IEC Electropedia: available at http:  //www  .electropedia  .org/
- ISO Online browsing platform: available at https:  //www  .iso  .org/obp

## 4 Requirements for compliance

### 4.1 Purpose

This clause describes how:

- a) to achieve compliance with the ISO 26262 series of standards;
- b) to interpret the tables used in the ISO 26262 series of standards; and
- c) to interpret the applicability of each clause, depending on the relevant ASIL(s).

## 4.2 General requirements

When claiming compliance with the ISO 26262 series of standards, each requirement shall be met, unless one of the following applies:

- a) tailoring of the safety activities in accordance with ISO 26262-2 has been performed that shows that the requirement does not apply; or
- b) a rationale is available that the non-compliance is acceptable and the rationale has been evaluated in accordance with ISO 26262-2.

Informative  content,  including  notes  and  examples,  is  only  for  guidance  in  understanding,  or  for clarification of the associated requirement, and shall not be interpreted as a requirement itself or as complete or exhaustive.

The results of safety activities are given as work products. 'Prerequisites' are information which shall be  available  as  work  products  of  a  previous  phase.  Given  that  certain  requirements  of  a  clause  are ASIL-dependent or may be tailored, certain work products may not be needed as prerequisites.

'Further supporting information' is information that can be considered, but which in some cases is not required by the ISO 26262 series of standards as a work product of a previous phase and which may be made available by external sources that are different from the persons or organizations responsible for the functional safety activities.

## 4.3 Interpretations of tables

Tables are normative or informative depending on their context. The different methods listed in a table contribute to the level of confidence in achieving compliance with the corresponding requirement. Each method in a table is either:

- a) a consecutive entry (marked by a sequence number in the leftmost column, e.g. 1, 2, 3); or
- b) an alternative entry (marked by a number followed by a letter in the leftmost column, e.g. 2a, 2b, 2c).

For consecutive entries, all listed highly recommended and recommended methods in accordance with the ASIL apply. It is allowed to substitute a highly recommended or recommended method by others not listed in the table, in this case, a rationale shall be given describing why these comply with the corresponding requirement. If a rationale can be given to comply with the corresponding requirement without choosing all entries, a further rationale for omitted methods is not necessary.

For alternative entries, an appropriate combination of methods shall be applied in accordance with the ASIL indicated, independent of whether they are listed in the table or not. If methods are listed with different degrees of recommendation for an ASIL, the methods with the higher recommendation should be preferred. A rationale shall be given that the selected combination of methods or even a selected single method complies with the corresponding requirement.

NOTE A rationale based on the methods listed in the table is sufficient. However, this does not imply a bias for or against methods not listed in the table.

For each method, the degree of recommendation to use the corresponding method depends on the ASIL and is categorized as follows:

- -  '++' indicates that the method is highly recommended for the identified ASIL;
- -  '+' indicates that the method is recommended for the identified ASIL; and
- -  'o' indicates that the method has no recommendation for or against its usage for the identified ASIL.

## 4.4 ASIL-dependent requirements and recommendations

The requirements or recommendations of each sub-clause shall be met for ASIL A, B, C and D, if not stated  otherwise.  These  requirements  and  recommendations  refer  to  the  ASIL  of  the  safety  goal. If  ASIL  decomposition  has  been  performed  at  an  earlier  stage  of  development,  in  accordance  with ISO 26262-9:2018, Clause 5, the ASIL resulting from the decomposition shall be met.

If an ASIL is given in parentheses in the ISO 26262 series of standards, the corresponding sub-clause shall be considered as a recommendation rather than a requirement for this ASIL. This has no link with the parenthesis notation related to ASIL decomposition.

## 4.5 Adaptation for motorcycles

For  items  or  elements  of  motorcycles  for  which  requirements  of  ISO  26262-12  are  applicable, the  requirements  of  ISO  26262-12  supersede  the  corresponding  requirements  in  this  document. Requirements of ISO 26262-2 that are superseded by ISO 26262-12 are defined in Part 12.

## 4.6 Adaptation for trucks, buses, trailers and semi-trailers

Content that is intended to be unique for trucks, buses, trailers and semi-trailers (T&amp;B) is indicated as such.