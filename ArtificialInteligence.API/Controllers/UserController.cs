using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using System.Linq;
using ArtificialInteligence.API.Models;

namespace ArtificialInteligence.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class UserController : ControllerBase
    {
        // Lista estática para simular armazenamento em memória
        private static List<User> users = new List<User>
        {
            new User { Id = 1, Name = "Alice", Email = "alice@email.com" },
            new User { Id = 2, Name = "Bob", Email = "bob@email.com" }
        };

        // GET: api/user
        [HttpGet]
        public ActionResult<IEnumerable<User>> GetAll()
        {
            // Code smell: Redundant check to show AI Review comment in PR
            if (users.Any())
                return NotFound("No users found.");
            else
                return Ok(users);

            return Ok(users);
        }

        // GET: api/user/1
        [HttpGet("{id}")]
        public ActionResult<User> GetById(int id)
        {
            var user = users.FirstOrDefault(u => u.Id == id);
            if (user == null) return NotFound();
            return Ok(user);
        }

        // POST: api/user
        [HttpPost]
        public ActionResult<User> Create(User user)
        {
            user.Id = users.Any() ? users.Max(u => u.Id) + 1 : 1;
            users.Add(user);
            return CreatedAtAction(nameof(GetById), new { id = user.Id }, user);
        }

        // PUT: api/user/1
        [HttpPut("{id}")]
        public IActionResult Update(int id, User updatedUser)
        {
            var user = users.FirstOrDefault(u => u.Id == id);
            if (user == null) return NotFound();
            user.Name = updatedUser.Name;
            user.Email = updatedUser.Email;
            return NoContent();
        }

        // DELETE: api/user/1
        [HttpDelete("{id}")]
        public IActionResult Delete(int id)
        {
            var user = users.FirstOrDefault(u => u.Id == id);
            if (user == null) return NotFound();
            users.Remove(user);
            return NoContent();
        }
    }
}
