function animateSpeedometer(targetScore) {
    const needle = document.getElementById('needle');
    const scoreValue = document.getElementById('score-value');
    
    // Calculate rotation angle (300-900 maps to -90 to 90 degrees)
    const minScore = 300;
    const maxScore = 900;
    const minAngle = -90;  // Starting angle (leftmost position)
    const maxAngle = 90;   // Ending angle (rightmost position)
    
    // Calculate target angle
    const targetAngle = minAngle + (targetScore - minScore) * (maxAngle - minAngle) / (maxScore - minScore);
    
    // Animate the needle
    setTimeout(() => {
        needle.style.transform = `rotate(${targetAngle}deg)`;
    }, 100);
    
    // Animate the score value
    let currentScore = 300;
    const increment = Math.ceil((targetScore - currentScore) / 50);
    
    const scoreInterval = setInterval(() => {
        currentScore += increment;
        
        if (currentScore >= targetScore) {
            currentScore = targetScore;
            clearInterval(scoreInterval);
            
            // Add a pulse effect when the score reaches the target
            scoreValue.style.transition = 'transform 0.5s ease-in-out';
            scoreValue.style.transform = 'scale(1.2)';
            
            setTimeout(() => {
                scoreValue.style.transform = 'scale(1)';
            }, 500);
        }
        
        scoreValue.textContent = currentScore;
    }, 40);
}