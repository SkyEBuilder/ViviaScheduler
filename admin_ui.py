import sys
import os
import json
import uuid
import datetime as DT
import gradio as gr

# Ensure src is in python path to import vivia_v4 modules
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from vivia_v4.api.config import settings
from vivia_v4.api.manager import UserManager, PoolManager
from vivia_v4.templates import ExactDateTask, FixedPeriodTask
from vivia_v4.model_definitions import TimeDelta

# --- Authentication Logic ---
def check_auth(secret):
    """Simple check against the admin secret in settings."""
    return secret == settings.admin_secret

# --- User Management Logic ---
def list_users():
    """Reads users directly using UserManager logic."""
    users = UserManager._load_users()
    if not users:
        return []
    # Convert dict to list for Dataframe
    data = []
    for api_key, u in users.items():
        data.append([u.get("user_id"), u.get("email"), str(u.get("is_active")), api_key])
    return data

def create_new_user(email):
    try:
        user = UserManager.create_user(email, is_active=True)
        return f"Success: Created user {email}", list_users()
    except Exception as e:
        return f"Error: {str(e)}", list_users()

def delete_user(api_key_to_delete):
    try:
        users = UserManager._load_users()
        if api_key_to_delete in users:
            del users[api_key_to_delete]
            UserManager._save_users(users)
            return f"Success: Deleted user with key {api_key_to_delete}", list_users()
        return "Error: User not found", list_users()
    except Exception as e:
        return f"Error: {str(e)}", list_users()

# --- Task Management Logic ---
def get_user_dropdown_choices():
    users = UserManager._load_users()
    # Return list of (label, value) tuples
    return [(f"{u['email']} ({u['user_id']})", u['user_id']) for u in users.values()]

def load_user_pool_json(user_id):
    if not user_id:
        return None, "Please select a user."
    try:
        pool = PoolManager.load_pool(user_id)
        return pool.model_dump_json(indent=2), f"Loaded pool for user {user_id}"
    except Exception as e:
        return None, f"Error loading pool: {str(e)}"

def save_user_pool_json(user_id, json_str):
    if not user_id:
        return "Error: No user selected."
    try:
        data = json.loads(json_str)
        # Validate by loading into model
        from vivia_v4.task_pool import ViviaTaskPool
        pool = ViviaTaskPool.model_validate(data)
        PoolManager.save_pool(user_id, pool)
        return f"Success: Pool updated for user {user_id}"
    except Exception as e:
        return f"Error validating/saving pool: {str(e)}"

def add_exact_date_task(user_id, name, mandatory, priority, repetition, start_iso, end_iso, duration_sec):
    if not user_id:
        return "Error: No user selected.", None

    try:
        # Parse Dates
        start_dt = DT.datetime.fromisoformat(start_iso)
        end_dt = DT.datetime.fromisoformat(end_iso)
        
        # Ensure Timezones (Default to UTC if missing)
        if start_dt.tzinfo is None: start_dt = start_dt.replace(tzinfo=DT.timezone.utc)
        if end_dt.tzinfo is None: end_dt = end_dt.replace(tzinfo=DT.timezone.utc)

        # Create Task Object
        task = ExactDateTask(
            name=name,
            mandatory=mandatory,
            priority=int(priority),
            repeatition=int(repetition),
            start_interval=(start_dt, start_dt),
            end_interval=(end_dt, end_dt),
            duration_interval=(DT.timedelta(seconds=float(duration_sec)), DT.timedelta(seconds=float(duration_sec)))
        )
        
        # Save to Pool
        pool = PoolManager.load_pool(user_id)
        pool.add_task(task)
        PoolManager.save_pool(user_id, pool)
        
        return f"Success: Added task '{name}'", pool.model_dump_json(indent=2)
    except Exception as e:
        return f"Error adding task: {str(e)}", None

# --- Gradio UI Layout ---
with gr.Blocks(title="ViviaScheduler Admin", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📅 ViviaScheduler Admin Interface")
    
    # State for authentication
    auth_state = gr.State(False)

    # --- Login Section ---
    with gr.Row() as login_row:
        secret_input = gr.Textbox(label="Admin Secret", type="password", placeholder="Enter admin secret...")
        login_btn = gr.Button("Login", variant="primary")
    
    login_msg = gr.Markdown("")

    # --- Main Dashboard (Hidden until login) ---
    with gr.Group(visible=False) as dashboard:
        with gr.Tabs():
            
            # === Tab 1: User Management ===
            with gr.Tab("👥 User Management"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Create User")
                        new_email = gr.Textbox(label="Email Address")
                        create_btn = gr.Button("Create Active User")
                        
                        gr.Markdown("### Delete User")
                        del_key = gr.Textbox(label="API Key to Delete")
                        del_btn = gr.Button("Delete User", variant="stop")
                        
                        create_status = gr.Markdown()
                    
                    with gr.Column(scale=2):
                        gr.Markdown("### Existing Users")
                        refresh_users = gr.Button("Refresh List", size="sm")
                        user_table = gr.Dataframe(
                            headers=["User ID", "Email", "Active", "API Key"],
                            datatype=["str", "str", "str", "str"],
                            interactive=False
                        )

            # === Tab 2: Task Management ===
            with gr.Tab("📝 Task Management"):
                with gr.Row():
                    user_selector = gr.Dropdown(label="Select User to Manage", choices=[], interactive=True)
                    refresh_selector = gr.Button("🔄", size="sm", scale=0)
                
                with gr.Row():
                    # Left Column: JSON View / Edit
                    with gr.Column(scale=1):
                        gr.Markdown("### Current Task Pool (JSON)")
                        gr.Markdown("*You can edit the JSON directly below and click 'Validate & Save'.*")
                        pool_json = gr.Code(language="json", label="Pool Data", interactive=True)
                        save_pool_btn = gr.Button("Validate & Save Changes", variant="secondary")
                        task_status = gr.Markdown()
                    
                    # Right Column: Dynamic Add Form
                    with gr.Column(scale=1):
                        gr.Markdown("### Add New Task (Form)")
                        task_type_selector = gr.Dropdown(
                            choices=["ExactDateTask", "FixedPeriodTask"], 
                            value="ExactDateTask", 
                            label="Task Type"
                        )
                        
                        # --- Dynamic Form: Exact Date Task ---
                        with gr.Group(visible=True) as form_exact_date:
                            ed_name = gr.Textbox(label="Task Name")
                            with gr.Row():
                                ed_mandatory = gr.Checkbox(label="Mandatory", value=True)
                                ed_priority = gr.Number(label="Priority", value=1, precision=0)
                                ed_rep = gr.Number(label="Repetition", value=1, precision=0)
                            
                            ed_start = gr.Textbox(label="Start Time (ISO)", value="2024-01-01T09:00:00+00:00")
                            ed_end = gr.Textbox(label="End Time (ISO)", value="2024-01-01T17:00:00+00:00")
                            ed_dur = gr.Number(label="Duration (seconds)", value=3600)
                            
                            ed_add_btn = gr.Button("Add ExactDateTask", variant="primary")

                        # --- Dynamic Form: Fixed Period Task (Placeholder) ---
                        with gr.Group(visible=False) as form_fixed_period:
                            gr.Markdown("⚠️ **FixedPeriodTask UI is not fully implemented yet.**")
                            gr.Markdown("Complex nested structures (period_items) are best handled via raw JSON upload or specialized sub-forms.")
                            # You can add raw JSON editor here if needed
                        

    # --- Event Handling ---

    # Login
    def on_login(secret):
        if check_auth(secret):
            return {
                login_row: gr.update(visible=False),
                dashboard: gr.update(visible=True),
                login_msg: "✅ Logged in successfully",
                user_table: list_users(),
                user_selector: gr.update(choices=get_user_dropdown_choices())
            }
        return {login_msg: "❌ Invalid Secret"}

    login_btn.click(on_login, inputs=[secret_input], outputs=[login_row, dashboard, login_msg, user_table, user_selector])

    # User Management
    create_btn.click(create_new_user, inputs=[new_email], outputs=[create_status, user_table])
    del_btn.click(delete_user, inputs=[del_key], outputs=[create_status, user_table])
    refresh_users.click(list_users, outputs=user_table)

    # Task Management
    refresh_selector.click(lambda: gr.update(choices=get_user_dropdown_choices()), outputs=user_selector)
    user_selector.change(load_user_pool_json, inputs=[user_selector], outputs=[pool_json, task_status])
    
    # Save JSON Directly
    save_pool_btn.click(save_user_pool_json, inputs=[user_selector, pool_json], outputs=[task_status])

    # Dynamic Form Switching
    def switch_task_form(task_type):
        if task_type == "ExactDateTask":
            return gr.update(visible=True), gr.update(visible=False)
        else:
            return gr.update(visible=False), gr.update(visible=True)

    task_type_selector.change(switch_task_form, inputs=[task_type_selector], outputs=[form_exact_date, form_fixed_period])

    # Add Task Action
    ed_add_btn.click(
        add_exact_date_task, 
        inputs=[user_selector, ed_name, ed_mandatory, ed_priority, ed_rep, ed_start, ed_end, ed_dur],
        outputs=[task_status, pool_json]
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
