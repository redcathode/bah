<script>
    let scheduledEmails = [];

    async function fetchScheduledEmails() {
        if (typeof window !== 'undefined') { // Check if running in browser
            const response = await fetch('http://192.168.1.245:5000/api/scheduled_emails');
            scheduledEmails = await response.json();
        } else {
            scheduledEmails = [ // Placeholder for server-side rendering
                { id: 1, recipient: 'Server Side Recipient 1', subject: 'SSR Scheduled Email 1', date: 'Tomorrow' },
                { id: 2, recipient: 'Server Side Recipient 2', subject: 'SSR Scheduled Email 2', date: 'Later' },
            ];
        }
    }

    fetchScheduledEmails();
</script>

<div class="scheduled-emails-container">
    <h2>Scheduled Emails</h2>
    {#each scheduledEmails as email}
        <div class="scheduled-email-item">
            <p><strong>Recipient:</strong> {email.recipient}</p>
            <p><strong>Subject:</strong> {email.subject}</p>
            <p><strong>Date:</strong> {email.date}</p>
        </div>
    {/each}
</div>

<style>
    .scheduled-emails-container {
        padding: 1rem;
    }

    .scheduled-email-item {
        border: 1px solid #ccc;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 5px;
        background-color: white;
    }
</style>