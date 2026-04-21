# 1. Business Goals

## Primary Goal
The Nutritionist AI Agent is a free, web-based consumer application that acts as a personal nutrition assistant. It generates personalized meal plans and tracks calorie and macro intake based on each user's dietary restrictions, allergies, and cuisine preferences. Nutritional data is sourced from verified food databases. 

## Problem Statement
Most people lack access to a personalized nutritionist. Generic diet apps provide one-size-fits-all plans that ignore individual food culture, taste preferences, and dietary needs. The result is low adherence, frustration, and poor health outcomes.
Core Pain Points:

- Generic meal plans that don't match cultural or personal taste preferences
- Manual, tedious calorie and macro logging
- No intelligent adjustment when meals are missed or swapped
- Lack of dietary restriction awareness (allergies, intolerances, religious diets)

## Scope constraints
* No authentication or user accounts — guest session only
* No production deployment required — localhost is fine for first 5 phases
* Brazilian cuisine is the main food focus
* Free tier APIs only (USDA FoodData Central or a curated local dataset)


# 2. Phased Plan

## Phase 1 — Core Agent
Guest onboarding form (goal, allergies, cuisine preferences) → constructs a structured system prompt → agent returns a meal plan in a defined JSON schema. Add conversation history so the user can refine results across turns ("make it more Brazilian", "swap the lunch").

## Phase 2 — Tool Use
Agent gets access to a food database tool. The agent decides when to call a tool, how to pass results back into context, and how to handle tool failures. This is where the agent graduates from pure reasoning to acting on external data. 

## Phase 3 - UI
Make UI more beautiful with a meal plan to the right and the chat to the left

## Phase 4 — Observability & Evals
Log every prompt, tool call, and response. Create a module in which we can evaluate the model (eg, no allergens, calorie accuracy, JSON validity, relevance to cuisine preference). Run automated tests against your logged traces and iterate on the system prompt based on results.