"""
Professional Network Analyzer Plugin for Cheshire Cat AI
========================================================

This plugin enables analysis of professional networks, relationships, and competencies
based on user input about profiles, names, job titles, or specific skills.

Features:
- Profile identification and analysis
- Professional network mapping
- Colleague and collaborator discovery
- Geographic/company location tracking
- Skill mapping and competency analysis
- Work context identification

Use case: When identifying a profile, name, job title, or specific competency,
get information about people connected to that profile (colleagues, collaborators,
team members), including their geographic or company location, professional network
exploration, associated skills mapping, and work context identification.
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from cat.mad_hatter.decorators import tool, hook
from cat.log import log


# Configuration and constants
PLUGIN_NAME = "Professional Network Analyzer"
VERSION = "1.0.0"

# Sample data structures for demonstration
# In a real implementation, these would connect to actual APIs or databases
SAMPLE_PROFILES = {
    "mario_rossi": {
        "name": "Mario Rossi",
        "position": "Senior Software Engineer",
        "company": "TechCorp Italia",
        "location": "Milano, Italia",
        "skills": ["Python", "Machine Learning", "DevOps", "Cloud Computing"],
        "experience_years": 8,
        "team": "AI Development Team",
        "manager": "Laura Bianchi",
        "colleagues": ["Giuseppe Verde", "Anna Neri", "Francesco Blu"],
        "projects": ["Customer Analytics Platform", "Automated Reporting System"]
    },
    "laura_bianchi": {
        "name": "Laura Bianchi", 
        "position": "AI Team Lead",
        "company": "TechCorp Italia",
        "location": "Milano, Italia",
        "skills": ["Team Leadership", "AI Strategy", "Python", "Data Science"],
        "experience_years": 12,
        "team": "AI Development Team",
        "direct_reports": ["Mario Rossi", "Giuseppe Verde", "Anna Neri"],
        "colleagues": ["Roberto Giallo", "Silvia Rosa"],
        "projects": ["AI Strategy Roadmap", "Team Performance Optimization"]
    },
    "giuseppe_verde": {
        "name": "Giuseppe Verde",
        "position": "Data Scientist",
        "company": "TechCorp Italia",
        "location": "Milano, Italia", 
        "skills": ["Data Analysis", "Statistical Modeling", "R", "Python"],
        "experience_years": 5,
        "team": "AI Development Team",
        "manager": "Laura Bianchi",
        "colleagues": ["Mario Rossi", "Anna Neri"],
        "projects": ["Market Research Analytics", "Predictive Modeling Suite"]
    }
}

COMPANY_NETWORKS = {
    "TechCorp Italia": {
        "headquarters": "Milano, Italia",
        "offices": ["Roma", "Torino", "Napoli", "Bologna"],
        "departments": {
            "AI Development Team": ["Mario Rossi", "Laura Bianchi", "Giuseppe Verde", "Anna Neri"],
            "Frontend Team": ["Roberto Giallo", "Silvia Rosa", "Marco Viola"],
            "Backend Team": ["Luca Azzurro", "Francesca Arancione"]
        },
        "size": "200-500 employees",
        "industry": "Software Development"
    }
}

SKILL_NETWORKS = {
    "Python": ["Mario Rossi", "Laura Bianchi", "Giuseppe Verde", "Luca Azzurro"],
    "Machine Learning": ["Mario Rossi", "Giuseppe Verde", "Anna Neri"],
    "Team Leadership": ["Laura Bianchi", "Roberto Giallo"],
    "Data Science": ["Laura Bianchi", "Giuseppe Verde", "Anna Neri"]
}


@tool(return_direct=True)
def analyze_professional_profile(query, cat):
    """
    Analyze a professional profile based on name, job title, or company.
    Input should be a person's name, job title, or company name.
    """

    query = query.lower().strip()

    # Search for profile matches
    matches = []

    for profile_id, profile in SAMPLE_PROFILES.items():
        if (query in profile["name"].lower() or 
            query in profile["position"].lower() or 
            query in profile["company"].lower()):
            matches.append(profile)

    if not matches:
        return f"Nessun profilo trovato per '{query}'. Prova con un nome, posizione o azienda diversi."

    result = f"🔍 **Analisi Profilo Professionale per '{query}'**\n\n"

    for profile in matches:
        result += f"**{profile['name']}**\n"
        result += f"📋 Posizione: {profile['position']}\n"
        result += f"🏢 Azienda: {profile['company']}\n"
        result += f"📍 Località: {profile['location']}\n"
        result += f"⚡ Competenze: {', '.join(profile['skills'])}\n"
        result += f"📅 Esperienza: {profile['experience_years']} anni\n"
        result += f"👥 Team: {profile['team']}\n\n"

        # Add network connections
        if "colleagues" in profile:
            result += f"👔 **Colleghi**: {', '.join(profile['colleagues'])}\n"
        if "manager" in profile:
            result += f"👨‍💼 **Manager**: {profile['manager']}\n"
        if "direct_reports" in profile:
            result += f"👥 **Collaboratori Diretti**: {', '.join(profile['direct_reports'])}\n"

        result += "\n---\n\n"

    return result


@tool(return_direct=True) 
def explore_professional_network(person_name, cat):
    """
    Explore the professional network of a specific person.
    Input should be the full name of the person whose network you want to explore.
    """

    person_name = person_name.strip()

    # Find the person's profile
    target_profile = None
    for profile_id, profile in SAMPLE_PROFILES.items():
        if person_name.lower() in profile["name"].lower():
            target_profile = profile
            break

    if not target_profile:
        return f"Profilo non trovato per '{person_name}'. Verifica il nome e riprova."

    result = f"🕸️ **Rete Professionale di {target_profile['name']}**\n\n"

    # Direct connections
    result += "**🔗 Connessioni Dirette:**\n"

    all_connections = set()
    if "colleagues" in target_profile:
        all_connections.update(target_profile["colleagues"])
    if "manager" in target_profile:
        all_connections.add(target_profile["manager"])
    if "direct_reports" in target_profile:
        all_connections.update(target_profile["direct_reports"])

    for connection in all_connections:
        # Find connection details
        conn_profile = None
        for prof_id, prof in SAMPLE_PROFILES.items():
            if connection in prof["name"]:
                conn_profile = prof
                break

        if conn_profile:
            result += f"  • **{connection}** - {conn_profile['position']} ({conn_profile['location']})\n"
        else:
            result += f"  • **{connection}**\n"

    # Team analysis
    result += f"\n**👥 Analisi Team ({target_profile['team']}):**\n"
    company = target_profile["company"]
    if company in COMPANY_NETWORKS:
        team_members = COMPANY_NETWORKS[company]["departments"].get(target_profile["team"], [])
        result += f"  • Membri del team: {len(team_members)}\n"
        result += f"  • Altri membri: {', '.join([m for m in team_members if m != target_profile['name']])}\n"

    # Skill overlap analysis
    result += f"\n**🎯 Analisi Competenze Condivise:**\n"
    for skill in target_profile["skills"]:
        if skill in SKILL_NETWORKS:
            peers = [p for p in SKILL_NETWORKS[skill] if p != target_profile["name"]]
            if peers:
                result += f"  • **{skill}**: condiviso con {', '.join(peers)}\n"

    return result


@tool(return_direct=True)
def map_company_network(company_name, cat):
    """
    Map the organizational network of a specific company.
    Input should be the company name.
    """

    company_name = company_name.strip()

    # Find company
    target_company = None
    for company, data in COMPANY_NETWORKS.items():
        if company_name.lower() in company.lower():
            target_company = company
            break

    if not target_company:
        return f"Azienda '{company_name}' non trovata nel database."

    company_data = COMPANY_NETWORKS[target_company]

    result = f"🏢 **Mappa Rete Aziendale: {target_company}**\n\n"

    result += f"📍 **Sede principale**: {company_data['headquarters']}\n"
    result += f"🏢 **Uffici**: {', '.join(company_data['offices'])}\n"
    result += f"👥 **Dimensione**: {company_data['size']}\n"
    result += f"🏭 **Settore**: {company_data['industry']}\n\n"

    result += "**🏗️ Struttura Organizzativa:**\n"

    for dept, members in company_data["departments"].items():
        result += f"\n**{dept}** ({len(members)} membri):\n"

        # Get detailed info for each member
        for member in members:
            member_profile = None
            for prof_id, prof in SAMPLE_PROFILES.items():
                if member in prof["name"]:
                    member_profile = prof
                    break

            if member_profile:
                result += f"  • **{member}** - {member_profile['position']}\n"
                result += f"    └ Competenze: {', '.join(member_profile['skills'][:3])}\n"
            else:
                result += f"  • **{member}**\n"

    return result


@tool(return_direct=True)
def analyze_skill_network(skill_name, cat):
    """
    Analyze the network of people with a specific skill or competency.
    Input should be the name of a skill or competency.
    """

    skill_name = skill_name.strip()

    # Find skill matches
    matching_skills = []
    for skill in SKILL_NETWORKS.keys():
        if skill_name.lower() in skill.lower():
            matching_skills.append(skill)

    if not matching_skills:
        return f"Competenza '{skill_name}' non trovata. Prova con: {', '.join(SKILL_NETWORKS.keys())}"

    result = f"🎯 **Analisi Rete Competenze: {skill_name}**\n\n"

    for skill in matching_skills:
        people = SKILL_NETWORKS[skill]
        result += f"**{skill}** ({len(people)} persone):\n"

        # Get profile details for each person
        for person in people:
            person_profile = None
            for prof_id, prof in SAMPLE_PROFILES.items():
                if person in prof["name"]:
                    person_profile = prof
                    break

            if person_profile:
                result += f"  • **{person}**\n"
                result += f"    └ {person_profile['position']} @ {person_profile['company']}\n"
                result += f"    └ {person_profile['location']} | {person_profile['experience_years']} anni exp.\n"

                # Show related skills
                other_skills = [s for s in person_profile['skills'] if s != skill]
                if other_skills:
                    result += f"    └ Altre competenze: {', '.join(other_skills[:3])}\n"
            else:
                result += f"  • **{person}**\n"

            result += "\n"

        result += "\n"

    # Network analysis
    result += "**📊 Analisi Rete:**\n"
    total_people = len(set().union(*[SKILL_NETWORKS[s] for s in matching_skills]))
    result += f"  • Persone totali con questa competenza: {total_people}\n"

    # Find skill intersections
    result += "  • Competenze correlate:\n"
    for other_skill, other_people in SKILL_NETWORKS.items():
        if other_skill not in matching_skills:
            overlap = set(SKILL_NETWORKS[matching_skills[0]]) & set(other_people)
            if overlap:
                result += f"    └ **{other_skill}**: {len(overlap)} persone in comune\n"

    return result


@tool(return_direct=True)
def identify_work_context(context_query, cat):
    """
    Identify work contexts, projects, and professional relationships.
    Input should describe a work context, project, or professional situation.
    """

    context_query = context_query.lower().strip()

    result = f"🔍 **Identificazione Contesto Lavorativo: '{context_query}'**\n\n"

    # Search across projects
    project_matches = []
    for profile_id, profile in SAMPLE_PROFILES.items():
        if "projects" in profile:
            for project in profile["projects"]:
                if any(word in project.lower() for word in context_query.split()):
                    project_matches.append({
                        "project": project,
                        "person": profile["name"],
                        "position": profile["position"],
                        "team": profile["team"]
                    })

    if project_matches:
        result += "**📋 Progetti Correlati:**\n"
        projects_seen = set()
        for match in project_matches:
            if match["project"] not in projects_seen:
                result += f"\n**{match['project']}**\n"

                # Find all people on this project
                project_team = [m for m in project_matches if m["project"] == match["project"]]
                for member in project_team:
                    result += f"  • {member['person']} - {member['position']}\n"

                projects_seen.add(match["project"])

    # Search across teams and departments
    result += "\n**👥 Team e Dipartimenti Correlati:**\n"
    for company, company_data in COMPANY_NETWORKS.items():
        for dept, members in company_data["departments"].items():
            if any(word in dept.lower() for word in context_query.split()):
                result += f"\n**{dept} @ {company}:**\n"
                result += f"  • Membri: {', '.join(members)}\n"
                result += f"  • Località: {company_data['headquarters']}\n"

    # Search across skills and competencies  
    skill_matches = []
    for skill, people in SKILL_NETWORKS.items():
        if any(word in skill.lower() for word in context_query.split()):
            skill_matches.append((skill, people))

    if skill_matches:
        result += "\n**🎯 Competenze Correlate:**\n"
        for skill, people in skill_matches:
            result += f"\n**{skill}:**\n"
            result += f"  • Esperti: {', '.join(people)}\n"

    if not project_matches and not skill_matches:
        result += "Nessun contesto lavorativo specifico trovato. Prova con termini come 'AI', 'development', 'analytics', 'team lead', etc.\n"

    return result


@hook
def agent_prompt_prefix(prefix, cat):
    """Customize the agent to be a professional network analysis expert."""

    prefix = f"""You are a Professional Network Analysis Expert powered by the Cheshire Cat AI framework.

You specialize in analyzing professional relationships, organizational structures, and competency networks. You help users:

1. **Identify and analyze professional profiles** based on names, job titles, or companies
2. **Map professional networks** and relationships between colleagues, collaborators, and team members  
3. **Explore organizational structures** and departmental connections
4. **Analyze skill networks** and competency distributions
5. **Identify work contexts** including projects, teams, and professional environments
6. **Provide geographic and company location insights** for professional contacts

You have access to specialized tools for professional network analysis. When users ask about:
- People, profiles, names, or job titles → use analyze_professional_profile
- Professional networks or relationships → use explore_professional_network  
- Company structures or organizations → use map_company_network
- Skills, competencies, or expertise → use analyze_skill_network
- Work contexts, projects, or teams → use identify_work_context

Always provide detailed, structured information with clear insights about professional relationships and networks. Use emojis to make responses more readable and engaging.

Remember: You're analyzing professional networks to help users understand relationships, collaborations, and competency distributions in workplace environments."""

    return prefix


@hook
def before_cat_sends_message(final_output, cat):
    """Enhance responses with professional network analysis context."""

    # Add professional network analysis branding
    if "🔍" in final_output.content or "🕸️" in final_output.content or "🏢" in final_output.content:
        footer = "\n\n---\n*💼 Analisi fornita dal Professional Network Analyzer Plugin*"
        final_output.content += footer

    return final_output


# Settings schema for the plugin
@hook
def settings_schema():
    """Define plugin settings."""
    return {
        "title": "Professional Network Analyzer Settings",
        "type": "object",
        "properties": {
            "enable_detailed_analysis": {
                "title": "Enable Detailed Analysis",
                "type": "boolean",
                "default": True,
                "description": "Enable detailed professional network analysis"
            },
            "include_geographic_data": {
                "title": "Include Geographic Data", 
                "type": "boolean",
                "default": True,
                "description": "Include geographic and location information in analysis"
            },
            "max_network_depth": {
                "title": "Maximum Network Depth",
                "type": "integer",
                "default": 3,
                "minimum": 1,
                "maximum": 5,
                "description": "Maximum depth for network relationship analysis"
            }
        }
    }
