explainer = """We classify our tools into three levels based on the potential risk to people and property. Tools are marked with coloured dots to help you identify whether you can use them or not.

You can check whether you're an authorised operator for specific medium and high risk tools by tapping the buttons below.

If we notice you using a tool inappropriately, we’ll still ask you to pause your job and help you identify a safer method."""

low_risk_header = "Low Risk 🟢"
low_risk_explainer = "You can self assess your competency on these tools and use them if you feel comfortable. Feel free to have a go and if you're not sure you can always ask for help. Even though these tools are low risk you should still be vigilant about safety."
low_risk_context = "This includes hand tools and some power tools. Since we don't track sign offs on low risk tools they're not listed individually here."

medium_risk_header = "Medium Risk 🟡"
medium_risk_explainer = "These tools can easily hurt you, others, or the tool. To use these tools you must either complete a short induction with one of our authorised trainers or demonstrate to them that you can use this tool safely."

high_risk_header = "High Risk 🔴"
high_risk_explainer = "These tools can cause serious injury, are easy to damage, or both. An induction with an authorised trainer is required before using these tools. You must go through the Artifactory’s training on high risk tools, even if you have used similar (or identical) tools elsewhere."

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

check_in_explainer_trainer = "This tool needs a follow up with the operator after {} days. A trainer can check in with the operator using the buttons below. I will send the original trainer a reminder if this isn't actioned by: {}"
check_in_explainer_finished = "This tool needed a follow up with the operator after {} days. Details of this check in can be found below."
check_in_no_slack = "This user does not have an associated Slack account so I can't open a direct message with them. A committee member can contact the operator <https://artifactory.tidyhq.com/contacts/{}|here>."

checkin_explainer_operator = """This is in relation to the {} induction you completed {} days ago.
We've found that a key part of the learning process is to put the knowledge you've learned into practice soon after its been acquired. For certain inductions this involves a check in with a trainer to ensure you've had an opportunity to use the tool, cement your learning, and ask any questions you may have.

Please indicate:

* If you've used the tool since your induction
* If you have any questions or concerns"""

checkin_induction_approved = "Your {} induction has been maintained. Unless something changes about the tool or we identify it's been a long time since you've used it I won't contact you about it again."
checkin_induction_rejected = "Unfortunately your {} induction has been revoked. Please arrange with a trainer to undergo a refresher induction before using this tool again."


trainee_messages = {}
trainee_messages[
    "member_induction"
] = """<@{trainer}> has just signed you off as having completed your new member induction! :tada:

As a recap of what was covered, you should now be familiar with:
• Where to find our <https://wiki.artifactory.org.au/en/constitution|Constitution> and <https://wiki.artifactory.org.au/en/docs/policies/bylaws|by-laws>
• Our <https://wiki.artifactory.org.au/en/docs/committee/code_of_conduct|Code of Conduct>
• How to pay your membership and tool usage fees (Your individual transfer code is `TC{trainee_tidyhq_id}`, this should be used in the description of all bank transfers you make to us)
• How to pause or resign your membership (email <mailto:membership@artifactory.org.au|membership@artifactory.org.au>)
• How to report injuries, request lockers, apply for a key, and other member services (`/form`)
• Where you can store items in the space
• Our <https://wiki.artifactory.org.au/en/docs/policies/trainingy|training policy>, including how to book training sessions and view your existing sign offs (like this one!)
• Rules around communal materials
• Where to find upcoming events and how to RSVP for the events that require it
• Items around the workshop including the kitchen, whiteboard, first aid kits, defibrillator, fire extinguishers, and emergency exits

If you have any questions about any of this, feel free to reach out to our Membership Officer <@UC6T4U150> or any committee member.
"""
