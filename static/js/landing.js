// Landing page animations and interactions

function goToDashboard() {
  window.location.href = "/dashboard"
}

// Smooth scroll for any future links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault()
    const target = document.querySelector(this.getAttribute("href"))
    if (target) {
      target.scrollIntoView({ behavior: "smooth" })
    }
  })
})

// Add parallax effect to orbs
window.addEventListener("mousemove", (e) => {
  const orbs = document.querySelectorAll(".gradient-orb")
  const mouseX = e.clientX / window.innerWidth
  const mouseY = e.clientY / window.innerHeight

  orbs.forEach((orb, index) => {
    const speed = (index + 1) * 20
    const x = (mouseX - 0.5) * speed
    const y = (mouseY - 0.5) * speed
    orb.style.transform = `translate(${x}px, ${y}px)`
  })
})
