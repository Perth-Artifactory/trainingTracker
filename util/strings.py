explainer = """We classify our tools into three levels based on the potential risk to people and property. Tools are marked with coloured dots to help you identify whether you can use them or not.

You can check whether you're an authorised operator for specific medium and high risk tools by tapping the buttons below.

If we notice you using a tool inappropriately, we’ll still ask you to pause your job and help you identify a safer method."""

low_risk_header = "Low Risk 🟢"
low_risk_explainer = "You can self assess your competency on these tools and use them if you feel comfortable. Feel free to have a go and if you're not sure you can always ask for help. Even though these tools are low risk you should still be vigilant about safety."
low_risk_context = "This includes hand tools and some power tools. Since we don't track sign offs on low risk tools they're not listed individually here."

medium_risk_header = "Medium Risk 🟡"
medium_risk_explainer = "These tools can easily hurt you, others, or the tool. To use these tools you must either complete a short induction with one of our authorised trainers or demonstrate to them that you can use this tool safely."

high_risk_header = "High Risk 🔴"
high_risk_explainer = "These tools can cause serious injury, are easy to damage, or both. An induction is required before using these tools. You must go through the Artifactory’s training on high risk tools, even if you have used similar (or identical) tools elsewhere. Only specific people are authorised to train on specific high risk tools."

check_training_header = "Check your training"

requesting_training_header = "Requesting training"
requesting_training_explainer = "You can request training in #training-and-inductions. Some training for medium risk tools can be conducted ad hoc at the discretion of an authorised trainer. However, most training needs to be booked in advance through Slack. Training for some of our high risk tools represents a significant time investment for our volunteers, and as such is only available to members.\n\nTraining on certain high risk tools also has an attached cost. Casual attendees who pay for training that is offered to members free of charge will have the training cost refunded if they join as a member within 7 days of completing their training."

trained_tools_modal_explainer = "These are the medium and high risk tools in the categories you selected. ✅ indicates a tool you're authorised to use."
trained_tools_modal_picker_label = "Filter categories"
trained_tools_modal_picker_placeholder = "Select categories..."
no_tools = "You're not authorised to use any tools in this category. This may be because you haven't completed the required training, or because we were unable to automatically link your Slack and TidyHQ accounts."
no_tools_all = "You're not authorised to use any medium or high risk tools. This may be because you haven't completed the required training, or because we were unable to automatically link your Slack and TidyHQ accounts."

trainer_header = "Trainer tools"
trainer_explainer = "You are authorised to add, remove, and check the tool authorisations of other members. We trust that you will only sign off on tools that you are authorised to train on."
select_users_modal_picker_label = "Select a user"
select_users_modal_picker_placeholder = (
    "Only users with linked TidyHQ accounts are shown"
)
trainer_tools_modal_explainer = (
    "These are the medium and high risk tools the selected user is authorised to use."
)
trainer_no_tools = "This user is not authorised to use any medium or high risk tools. This may be because they haven't completed the required training, or because we were unable to automatically link their Slack and TidyHQ accounts."

trainer_add_explainer = "Check the boxes next to the tools you want to authorise this user to use. Tools the user is already authorised to use are not listed."
trainer_remove_explainer = "Check the boxes next to the tools you want to remove this user's authorisation to use. Tools the user is not authorised to use are not listed."

check_in_explainer_trainer = "This tool needs a follow up with the operator after {} days. You can check in with the operator using the buttons below. I will send you a reminder if you haven't checked in with the operator after by: {}"
check_in_no_slack = "This user does not have an associated Slack account so I can't open a direct message with them. A committee member can contact the operator <https://artifactory.tidyhq.com/contacts/{}|here>."
